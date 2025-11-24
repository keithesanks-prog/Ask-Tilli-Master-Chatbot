"""
Chat Router

REST API endpoint that mirrors the emt-api chat() function structure.
Provides conversational interface for SEL assessment analysis.
"""
import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict, Any

from ..models.chat_models import ChatRequest, ChatResponse
from ..services.llm_engine import LLMEngine
from ..services.security import InputSanitizer, SecurityError
from ..services.harmful_content_detector import HarmfulContentDetector
from ..services.audit_logger import FERPAAuditLogger
from ..middleware.auth import verify_token
from ..middleware.rate_limit import limiter, RATE_LIMITS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
llm_engine = LLMEngine()
harmful_content_detector = HarmfulContentDetector(enabled=True)
audit_logger = FERPAAuditLogger(enabled=True)

# System instruction for SEL chat (from emt-api)
SYSTEM_INSTRUCTION_CHAT = """
You are an expert in Social Emotional Learning (SEL).
You will be given score data for 4 assessments at the school level.
Use these scores to provide emotionally intelligent and insightful answers.
If the question is in Arabic, respond in Arabic.
If in English, respond in English.

Here are the 4 assessments:
1) child – A picture-based SEL assessment developed for Grade 1 students to measure the 8 foundational Tilli SEL skills. It draws from two established methods; Challenging Situation Tasks (CST) and Emotion Matching Tasks (EMT) and has been redesigned into a visual, interactive, multiple-choice format. Students are presented with illustrated scenarios and emotional expressions, and asked how they would think, feel, or respond. This approach directly assesses children's understanding, recognition, and application of SEL skills in developmentally appropriate, engaging ways.

2) parent – A caregiver questionnaire that measures the same 8 foundational SEL skills from the parent's perspective. It asks parents how often or how well their child demonstrates social and emotional behaviors in everyday situations, such as identifying emotions, showing empathy, or managing frustration. The Parent Report provides a view of the child's SEL development at home, complementing the student and teacher perspectives.

3) teacher_report – A teacher-completed survey that assesses the same 8 foundational SEL skills for each student from the teacher's point of view. Teachers rate how consistently and effectively students display SEL skills in classroom and school settings, such as emotional regulation, collaboration, empathy, and reflection. This report aligns directly with the student and parent assessments, offering a three-perspective understanding of each child's SEL profile across home and school contexts.

4) teacher_survey – A self-assessment for teachers that measures their own social and emotional competencies and classroom SEL practices, based on the same 8 foundational Tilli SEL skills. It explores areas such as self-awareness, emotional regulation, empathy, and relationship-building, while also reflecting on how teachers model and integrate SEL in their classrooms. The survey supports teacher wellbeing, professional growth, and the overall quality of SEL implementation.


You'll be given the following structure for the scores for each assessment:
{
  "testType": "PRE", // PRE or POST
  "totalStudents": 100,
  "school": "School Name",
  "assessment": "child", // child, parent, teacher_report, teacher_survey
  "overall_level_distribution": {"beginner":0,"growth":4,"expert":6}, // numbers are how many students are at each level
  "category_level_distributions": {
    "self_awareness":{"beginner":0,"growth":4,"expert":6}, // numbers are how many students are at each level of the skill
    "social_management":{"beginner":0,"growth":4,"expert":6}, // numbers are how many students are at each level of the skill
    "social_awareness":{"beginner":0,"growth":2,"expert":8}, // numbers are how many students are at each level of the skill
    "relationship_skills":{"beginner":4,"growth":3,"expert":3}, // numbers are how many students are at each level of the skill
    "responsible_decision_making":{"beginner":1,"growth":4,"expert":5}, // numbers are how many students are at each level of the skill
    "metacognition":{"beginner":0,"growth":3,"expert":7}, // numbers are how many students are at each level of the skill
    "empathy":{"beginner":0,"growth":7,"expert":3}, // numbers are how many students are at each level of the skill
    "critical_thinking":{"beginner":0,"growth":5,"expert":5} // numbers are how many students are at each level of the skill
  }
}
"""


@router.post("", response_model=ChatResponse)
@limiter.limit(RATE_LIMITS["ask"])
async def chat(
    request: Request,
    chat_request: ChatRequest,
    current_user: dict = Depends(verify_token)
) -> ChatResponse:
    """
    Chat endpoint that mirrors the emt-api chat() function structure.
    
    This endpoint:
    1. Accepts a message, SEL scores, and conversation history
    2. Builds conversation context with system instruction
    3. Generates response using Gemini API
    4. Returns plain text response
    
    Args:
        request: FastAPI Request object (for rate limiting)
        chat_request: ChatRequest with message, scores, and history
        current_user: Authenticated user information
        
    Returns:
        ChatResponse with the generated text
        
    Raises:
        HTTPException: For validation errors, security violations, or processing errors
    """
    try:
        # Step 0: Sanitize and validate inputs
        try:
            sanitized_message = InputSanitizer.sanitize_question(chat_request.message)
        except SecurityError as e:
            logger.warning(f"Security violation detected in chat message: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        
        # Step 0.5: Detect harmful content in message
        user_id = current_user.get('user_id', 'unknown')
        school_id = current_user.get('school_id')
        
        message_harm_detection = harmful_content_detector.detect_harmful_content(
            text=sanitized_message,
            context="chat_message",
            user_id=user_id,
            school_id=school_id
        )
        
        if message_harm_detection.get("is_harmful"):
            # Generate and log alert
            alert = harmful_content_detector.generate_alert(
                detection_result=message_harm_detection,
                text=sanitized_message,
                context="chat_message",
                user_id=user_id,
                school_id=school_id
            )
            harmful_content_detector.log_alert(alert)
            
            # Log to audit trail
            audit_logger.log_harmful_content(
                user_id=user_id,
                user_email=current_user.get('email'),
                school_id=school_id,
                severity=message_harm_detection.get("severity", "low"),
                harm_types=message_harm_detection.get("harm_types", []),
                context="chat_message",
                matches_count=len(message_harm_detection.get("matches", [])),
                text_preview=sanitized_message[:200] if sanitized_message else None,
                ip_address=request.client.host if request.client else None
            )
            
            # Block critical/high severity content
            if harmful_content_detector.should_block_response(message_harm_detection):
                logger.critical(
                    f"Blocked harmful chat message from user {user_id}: "
                    f"severity={message_harm_detection.get('severity')}"
                )
                raise HTTPException(
                    status_code=400,
                    detail="Your message contains content that cannot be processed. "
                           "If you believe this is an error, please contact support."
                )
        
        # Step 1: Build conversation context (matching emt-api structure)
        conversation = [SYSTEM_INSTRUCTION_CHAT]
        
        # Add SEL scores to context
        if chat_request.scores:
            conversation.append(f"School-level SEL scores: {chat_request.scores}")
        
        # Add conversation history
        for msg in chat_request.history:
            role = msg.role
            text = msg.text
            conversation.append(f"{role.capitalize()}: {text}")
        
        # Add current message
        conversation.append(f"User: {sanitized_message}")
        
        # Step 2: Generate response using LLM
        logger.info(
            f"Chat request from user {user_id}: "
            f"message_length={len(sanitized_message)}, "
            f"history_length={len(chat_request.history)}"
        )
        
        response_text = llm_engine.generate_chat_response(
            conversation=conversation,
            max_tokens=500
        )
        
        # Step 2.5: Detect harmful content in response
        response_harm_detection = harmful_content_detector.detect_harmful_content(
            text=response_text,
            context="chat_response",
            user_id=user_id,
            school_id=school_id
        )
        
        if response_harm_detection.get("is_harmful"):
            # Generate and log alert
            alert = harmful_content_detector.generate_alert(
                detection_result=response_harm_detection,
                text=response_text,
                context="chat_response",
                user_id=user_id,
                school_id=school_id
            )
            harmful_content_detector.log_alert(alert)
            
            # Log to audit trail
            audit_logger.log_harmful_content(
                user_id=user_id,
                user_email=current_user.get('email'),
                school_id=school_id,
                severity=response_harm_detection.get("severity", "low"),
                harm_types=response_harm_detection.get("harm_types", []),
                context="chat_response",
                matches_count=len(response_harm_detection.get("matches", [])),
                text_preview=response_text[:200] if response_text else None,
                ip_address=request.client.host if request.client else None
            )
            
            # Block critical/high severity content in response
            if harmful_content_detector.should_block_response(response_harm_detection):
                logger.critical(
                    f"Blocked harmful chat response to user {user_id}: "
                    f"severity={response_harm_detection.get('severity')}"
                )
                response_text = (
                    "I'm unable to provide a complete response at this time. "
                    "Please rephrase your question or contact support for assistance."
                )
        
        # Step 3: Log chat interaction for audit trail
        audit_logger.log_data_access(
            user_id=user_id,
            user_email=current_user.get('email', 'unknown'),
            user_role=current_user.get('role', 'educator'),
            school_id=school_id or 'unknown',
            action="chat",
            purpose="SEL assessment analysis via chat interface",
            question=sanitized_message,
            data_sources_accessed=["SEL_SCORES"],
            ip_address=request.client.host if request.client else None,
            metadata={
                "response_length": len(response_text) if response_text else 0,
                "history_length": len(chat_request.history),
                "has_scores": bool(chat_request.scores)
            }
        )
        
        return ChatResponse(response=response_text)
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except SecurityError as e:
        logger.error(f"Security error in chat: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Invalid input detected. Please check your request."
        )
    
    except Exception as e:
        # Log full error internally but don't expose details to client
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your request. Please try again later."
        )
