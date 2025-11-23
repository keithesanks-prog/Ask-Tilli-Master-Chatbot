"""
Agent Router

Main endpoint for the Master Agent that handles educator questions.
"""
import logging
import re
from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime

from ..models.query_models import AskRequest, AskResponse
from ..services.data_router import DataRouter
from ..services.llm_engine import LLMEngine
from ..services.security import InputSanitizer, SecurityError
from ..services.harmful_content_detector import HarmfulContentDetector
from ..services.audit_logger import FERPAAuditLogger
from ..middleware.auth import verify_token
from ..middleware.rate_limit import limiter, RATE_LIMITS
from ..services import csv_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])
data_router = DataRouter()
llm_engine = LLMEngine()
harmful_content_detector = HarmfulContentDetector(enabled=True)
audit_logger = FERPAAuditLogger(enabled=True)

COMPARISON_KEYWORDS = [
    "before", "after", "growth", "change", "progress", "improve", "improvement", "compare", "comparison", "trend"
]

def _needs_prepost_comparison(question: str) -> bool:
    q = (question or "").lower()
    return any(k in q for k in COMPARISON_KEYWORDS)


@router.post("/ask", response_model=AskResponse)
@limiter.limit(RATE_LIMITS["ask"])
async def ask_question(
    request: Request,
    ask_request: AskRequest,
    current_user: dict = Depends(verify_token)
) -> AskResponse:
    """
    Main endpoint for educator questions.
    
    This endpoint:
    1. Validates and sanitizes input
    2. Parses the educator's question
    3. Determines which data sources are needed
    4. Fetches data from relevant assessment tables
    5. Formats data for LLM consumption
    6. Generates a natural language response
    
    Args:
        request: FastAPI Request object (for rate limiting)
        ask_request: AskRequest containing the educator's question and optional filters
        current_user: Authenticated user information (from auth middleware)
        
    Returns:
        AskResponse with the generated answer and metadata
        
    Raises:
        HTTPException: For validation errors, security violations, or processing errors
    """
    try:
        # Step 0: Sanitize and validate all inputs
        try:
            sanitized_question = InputSanitizer.sanitize_question(ask_request.question)
            sanitized_student_id = InputSanitizer.sanitize_identifier(
                ask_request.student_id, 
                field_name="student_id"
            )
            # Extract school identifier from the question (e.g., "school 1" or "School A")
            # Extract school identifier from the question
            # Capture "school" followed by words, allowing for multi-word names like "Lincoln High"
            # Regex: school\s+ (one or more words)
            school_match = re.search(r"school\s+([\w\d\s]+?)(?=\s+(?:perform|score|result|do|did|is|was)|$|[?.,])", sanitized_question, re.IGNORECASE)
            extracted_school_raw = school_match.group(0) if school_match else None # "School Lincoln"
            extracted_school_name = school_match.group(1) if school_match else None # "Lincoln"
            
            extracted_school = extracted_school_raw # Keep full string for fetch_data (CSV likely needs "School X")

            # --- Data Access Control: School Isolation ---
            user_school_id = current_user.get("school_id")
            
            # If user has a school_id (educators/admins usually do), enforce it
            if user_school_id:
                if extracted_school_name:
                    # Robust matching: 
                    # 1. Normalize strings
                    # 2. Check if the CORE name (without "School") is present in the user's school ID
                    s_name = extracted_school_name.lower().strip()
                    s_user = user_school_id.lower().strip()
                    
                    # Check for overlap
                    if s_name not in s_user and s_user not in s_name:
                        logger.warning(
                            f"Access denied: User {current_user.get('user_id')} (School: {user_school_id}) "
                            f"attempted to access {extracted_school}"
                        )
                        raise HTTPException(
                            status_code=403,
                            detail=f"Access denied: You are not authorized to view data for {extracted_school}."
                        )
                else:
                    # If no school specified in question, default to user's school
                    extracted_school = user_school_id

            sanitized_classroom_id = InputSanitizer.sanitize_identifier(
                ask_request.classroom_id,
                field_name="classroom_id"
            )
            sanitized_grade_level = InputSanitizer.sanitize_grade_level(ask_request.grade_level)
        except SecurityError as e:
            logger.warning(f"Security violation detected: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        
        # Step 0.5: Detect harmful content in question
        user_id = current_user.get('user_id', 'unknown')
        school_id = current_user.get('school_id')
        
        question_harm_detection = harmful_content_detector.detect_harmful_content(
            text=sanitized_question,
            context="question",
            user_id=user_id,
            school_id=school_id
        )
        
        if question_harm_detection.get("is_harmful"):
            # Generate and log alert
            alert = harmful_content_detector.generate_alert(
                detection_result=question_harm_detection,
                text=sanitized_question,
                context="question",
                user_id=user_id,
                school_id=school_id,
                student_id=sanitized_student_id
            )
            harmful_content_detector.log_alert(alert)
            
            # Log to audit trail (FERPA/UNICEF compliance)
            audit_logger.log_harmful_content(
                user_id=user_id,
                user_email=current_user.get('email'),
                school_id=school_id,
                severity=question_harm_detection.get("severity", "low"),
                harm_types=question_harm_detection.get("harm_types", []),
                context="question",
                student_id=sanitized_student_id,
                matches_count=len(question_harm_detection.get("matches", [])),
                text_preview=sanitized_question[:200] if sanitized_question else None,
                ip_address=request.client.host if request.client else None,
                session_id=None,  # TODO: Get from session
                alert_metadata={"alert": alert}
            )
            
            # Block critical/high severity content
            if harmful_content_detector.should_block_response(question_harm_detection):
                logger.critical(
                    f"Blocked harmful question from user {user_id}: "
                    f"severity={question_harm_detection.get('severity')}, "
                    f"types={question_harm_detection.get('harm_types')}"
                )
                raise HTTPException(
                    status_code=400,
                    detail="Your question contains content that cannot be processed. "
                           "If you believe this is an error, please contact support."
                )
        
        # Step 0.75: Verify data access authorization (BEFORE data retrieval)
        # This enforces class-level and student-level authorization
        from ..middleware.data_access import verify_data_access
        try:
            await verify_data_access(
                current_user=current_user,
                student_id=sanitized_student_id,
                classroom_id=sanitized_classroom_id,
                grade_level=sanitized_grade_level
            )
        except HTTPException as e:
            # Log access denied event for audit
            audit_logger.log_security_event(
                user_id=user_id,
                user_email=current_user.get('email'),
                school_id=school_id,
                event_type="access_denied",
                severity="medium",
                description=f"Data access denied: student_id={sanitized_student_id}, classroom_id={sanitized_classroom_id}",
                ip_address=request.client.host if request.client else None,
                metadata={
                    "student_id": sanitized_student_id,
                    "classroom_id": sanitized_classroom_id,
                    "grade_level": sanitized_grade_level
                }
            )
            raise  # Re-raise the 403 Forbidden
        
        # Log request for audit trail
        logger.info(
            f"Request from user {current_user.get('user_id', 'unknown')}: "
            f"question_length={len(sanitized_question)}, "
            f"student_id={sanitized_student_id is not None}, "
            f"classroom_id={sanitized_classroom_id is not None}"
        )
        
        # Step 1: Determine which data sources are needed
        data_sources = data_router.determine_data_sources(sanitized_question)
        
        # Step 2: Fetch data from relevant sources
        dataset = data_router.fetch_data(
            data_sources=data_sources,
            grade_level=sanitized_grade_level,
            student_id=sanitized_student_id,
            classroom_id=sanitized_classroom_id,
            school=extracted_school
        )
        
        # Step 3: Format data for LLM
        data_summary = data_router.format_data_for_llm(dataset)
        
        # Step 3.5: If question implies pre/post comparison, build comparison summary from CSV
        # Basic heuristic: detect keywords and extract grade if present in request
        if _needs_prepost_comparison(sanitized_question):
            try:
                grade_hint = sanitized_grade_level or "Grade 1"  # default to Grade 1 if not provided
                pre_rows = csv_data.filter_scores(grade=grade_hint, test_type="pre")
                post_rows = csv_data.filter_scores(grade=grade_hint, test_type="post")
                comparison_summary = csv_data.build_comparison_summary(pre_rows, post_rows)
                # Attach to data summary so the LLM can use it
                data_summary["prepost_comparison"] = {
                    "grade": grade_hint,
                    "summary": comparison_summary
                }
            except Exception as e:
                logger.warning(f"Pre/Post comparison unavailable: {str(e)}")
        
        # Step 4: Generate response using LLM (prompt sanitization happens inside)
        answer = llm_engine.generate_response(
            question=sanitized_question,
            data_summary=data_summary
        )
        
        # Step 4.5: Detect harmful content in LLM response
        response_harm_detection = harmful_content_detector.detect_harmful_content(
            text=answer,
            context="response",
            user_id=user_id,
            school_id=school_id
        )
        
        if response_harm_detection.get("is_harmful"):
            # Generate and log alert
            alert = harmful_content_detector.generate_alert(
                detection_result=response_harm_detection,
                text=answer,
                context="response",
                user_id=user_id,
                school_id=school_id,
                student_id=sanitized_student_id
            )
            harmful_content_detector.log_alert(alert)
            
            # Log to audit trail (FERPA/UNICEF compliance)
            audit_logger.log_harmful_content(
                user_id=user_id,
                user_email=current_user.get('email'),
                school_id=school_id,
                severity=response_harm_detection.get("severity", "low"),
                harm_types=response_harm_detection.get("harm_types", []),
                context="response",
                student_id=sanitized_student_id,
                matches_count=len(response_harm_detection.get("matches", [])),
                text_preview=answer[:200] if answer else None,
                ip_address=request.client.host if request.client else None,
                session_id=None,  # TODO: Get from session
                alert_metadata={"alert": alert}
            )
            
            # Block critical/high severity content in response
            if harmful_content_detector.should_block_response(response_harm_detection):
                logger.critical(
                    f"Blocked harmful LLM response to user {user_id}: "
                    f"severity={response_harm_detection.get('severity')}, "
                    f"types={response_harm_detection.get('harm_types')}"
                )
                # Return a safe, generic response instead of harmful content
                answer = (
                    "I'm unable to provide a complete response at this time. "
                    "Please rephrase your question or contact support for assistance."
                )
        
        # Step 5: Determine confidence (placeholder logic)
        confidence = "high" if len(data_sources) >= 2 else "medium"
        if not data_sources:
            confidence = "low"
        
        # Step 6: Log data access for FERPA/UNICEF compliance
        audit_logger.log_data_access(
            user_id=user_id,
            user_email=current_user.get('email', 'unknown'),
            user_role=current_user.get('role', 'educator'),
            school_id=school_id or 'unknown',
            action="query",  # Action type
            purpose="Educational inquiry - analyzing student assessment data",  # UNICEF requirement: why data was accessed
            student_id=sanitized_student_id,
            classroom_id=sanitized_classroom_id,
            grade_level=sanitized_grade_level,
            question=sanitized_question,  # Length only, not full text
            data_sources_accessed=data_sources,
            ip_address=request.client.host if request.client else None,
            session_id=None,  # TODO: Get from session
            metadata={
                "confidence": confidence,
                "response_length": len(answer) if answer else 0,
                "data_sources_count": len(data_sources)
            }
        )
        
        return AskResponse(
            answer=answer,
            data_sources=data_sources,
            confidence=confidence
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (from security, validation, etc.)
        raise
    
    except SecurityError as e:
        logger.error(f"Security error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Invalid input detected. Please check your request."
        )
    
    except Exception as e:
        # Log full error internally but don't expose details to client
        logger.error(f"Error processing question: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your question. Please try again later."
        )

