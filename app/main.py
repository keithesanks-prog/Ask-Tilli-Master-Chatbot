"""
Master Agent FastAPI Application

Main entry point for the Master Agent service.
"""
import os
import logging
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .models.query_models import AskRequest, AskResponse, HealthResponse, SecurityHealthResponse
from .routers import agent, query, prompt_eval, test
from .routers import debug as debug_router
from .services.data_router import DataRouter
from .services.llm_engine import LLMEngine
from .middleware.rate_limit import limiter, _rate_limit_exceeded_handler
from .middleware.auth import verify_token
from .middleware.security_headers import SecurityHeadersMiddleware, TLSEnforcementMiddleware
from .middleware.fail_safe import FailSafeMiddleware
from .services.security import SecurityError, InputSanitizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import service manager for lifespan management
from .services.service_manager import lifespan

# Initialize FastAPI application with lifespan management
app = FastAPI(
    title="Master Agent API",
    description="Master Agent service for Tilli - routes educator questions to assessment data and generates insights",
    version="0.1.0",
    lifespan=lifespan  # Handles startup/shutdown with fail-safe behavior
)

# Configure rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# TLS/HTTPS Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
REQUIRE_TLS = os.getenv("REQUIRE_TLS", "false").lower() == "true" or ENVIRONMENT == "production"
ENFORCE_HTTPS = os.getenv("ENFORCE_HTTPS", "false").lower() == "true" or ENVIRONMENT == "production"
HSTS_MAX_AGE = int(os.getenv("HSTS_MAX_AGE", "31536000"))  # 1 year in seconds
HSTS_INCLUDE_SUBDOMAINS = os.getenv("HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
HSTS_PRELOAD = os.getenv("HSTS_PRELOAD", "false").lower() == "true"

# Allowed hosts for Host header validation
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]

# Add fail-safe middleware (should be early in middleware stack)
# This ensures requests are rejected when service is stopping (fail-safe behavior)
app.add_middleware(FailSafeMiddleware)
logger.info("Fail-safe middleware enabled (rejects requests when service is stopping)")

# Add TLS enforcement middleware (should be before fail-safe for HTTPS check)
if REQUIRE_TLS:
    logger.info("TLS enforcement enabled")
    app.add_middleware(
        TLSEnforcementMiddleware,
        require_tls=REQUIRE_TLS,
        allowed_hosts=ALLOWED_HOSTS if ALLOWED_HOSTS else None
    )

# Add security headers middleware
logger.info(f"Security headers enabled: HTTPS enforcement={ENFORCE_HTTPS}, HSTS max-age={HSTS_MAX_AGE}")
app.add_middleware(
    SecurityHeadersMiddleware,
    enforce_https=ENFORCE_HTTPS,
    hsts_max_age=HSTS_MAX_AGE,
    hsts_include_subdomains=HSTS_INCLUDE_SUBDOMAINS,
    hsts_preload=HSTS_PRELOAD,
)

# Configure CORS with security defaults
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000"  # Default for development
).split(",")

# In production, restrict to specific origins
if os.getenv("ENVIRONMENT", "development") == "production":
    if "*" in allowed_origins:
        logger.warning("CORS allows all origins in production! Restricting to whitelist.")
        allowed_origins = [
            origin for origin in allowed_origins 
            if origin.strip() != "*"
        ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only allow needed methods
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

# Initialize services
data_router = DataRouter()
llm_engine = LLMEngine()

# Include routers
app.include_router(agent.router)
app.include_router(query.router)
app.include_router(prompt_eval.router)
app.include_router(test.router)
app.include_router(debug_router.router)


@app.post("/ask", response_model=AskResponse, tags=["ask"])
@limiter.limit("10/minute")  # Rate limit the main endpoint
async def ask(
    request: Request,
    ask_request: AskRequest,
    current_user: dict = Depends(verify_token)  # Will be imported
) -> AskResponse:
    """
    Main endpoint for educator questions.
    
    This is the primary endpoint specified in requirements.
    It follows the same flow as /agent/ask with security measures.
    
    Args:
        request: FastAPI Request object (for rate limiting)
        ask_request: AskRequest containing the educator's question and optional filters
        current_user: Authenticated user information
        
    Returns:
        AskResponse with the generated answer and metadata
    """
    try:
        # Step 0: Sanitize and validate all inputs
        try:
            sanitized_question = InputSanitizer.sanitize_question(ask_request.question)
            sanitized_student_id = InputSanitizer.sanitize_identifier(
                ask_request.student_id, 
                field_name="student_id"
            )
            sanitized_classroom_id = InputSanitizer.sanitize_identifier(
                ask_request.classroom_id,
                field_name="classroom_id"
            )
            sanitized_grade_level = InputSanitizer.sanitize_grade_level(ask_request.grade_level)
        except SecurityError as e:
            logger.warning(f"Security violation: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        # Log request for audit trail
        logger.info(
            f"Request from user {current_user.get('user_id', 'unknown')}: "
            f"question_length={len(sanitized_question)}"
        )
        
        # Step 1: Determine which data sources are needed
        data_sources = data_router.determine_data_sources(sanitized_question)
        
        # Step 2: Fetch data from relevant sources
        dataset = data_router.fetch_data(
            data_sources=data_sources,
            grade_level=sanitized_grade_level,
            student_id=sanitized_student_id,
            classroom_id=sanitized_classroom_id
        )
        
        # Step 3: Format data for LLM
        data_summary = data_router.format_data_for_llm(dataset)
        
        # Step 4: Generate response using LLM
        answer = llm_engine.generate_response(
            question=sanitized_question,
            data_summary=data_summary
        )
        
        # Step 5: Determine confidence
        confidence = "high" if len(data_sources) >= 2 else "medium"
        if not data_sources:
            confidence = "low"
        
        return AskResponse(
            answer=answer,
            data_sources=data_sources,
            confidence=confidence
        )
    
    except SecurityError as e:
        logger.warning(f"Security error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Invalid input detected. Please check your request."
        )
    except HTTPException:
        raise
    except Exception as e:
        # Log full error internally but don't expose details to client
        logger.error(f"Error processing question: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your question. Please try again later."
        )


@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "service": "Master Agent API",
        "version": "0.1.0",
        "description": "Master Agent service for Tilli - answers educator questions using assessment data",
        "endpoints": {
            "ask": "/ask (also available at /agent/ask)",
            "health": "/health (basic health check)",
            "health_security": "/health/security (comprehensive security health check)",
            "query_sources": "/query/sources",
            "test_data": "/query/test-data",
            "prompt_eval": "/prompt-eval/receive (receives data from Prompt Eval Tool)"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
@limiter.limit("100/minute")
async def health_check(request: Request) -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns:
        HealthResponse with service status and version
    """
    return HealthResponse(
        status="healthy",
        version="0.1.0"
    )


@app.get("/health/security", response_model=SecurityHealthResponse, tags=["health"])
@limiter.limit("10/minute")  # Lower rate limit for security endpoint
async def security_health_check(request: Request) -> SecurityHealthResponse:
    """
    Comprehensive security health check endpoint.
    
    Validates that all security countermeasures are active and functioning:
    - TLS/HTTPS enforcement
    - Authentication configuration
    - Rate limiting
    - Input validation
    - Harmful content detection
    - Audit logging
    - External API (Gemini) connectivity
    - Security headers
    - CORS configuration
    
    Returns:
        SecurityHealthResponse with detailed security health status
        
    Example:
        ```json
        {
            "timestamp": "2024-01-01T12:00:00Z",
            "overall_status": "healthy",
            "service_version": "0.1.0",
            "checks": {
                "service": {"status": "healthy", ...},
                "transport_security": {"status": "healthy", ...},
                "authentication": {"status": "degraded", ...},
                ...
            },
            "summary": {
                "total_checks": 10,
                "healthy": 9,
                "degraded": 1,
                "critical": 0,
                "issues": [...]
            }
        }
        ```
    """
    from .services.security_health_check import SecurityHealthCheck
    
    health_checker = SecurityHealthCheck()
    health_status = health_checker.check_all()
    
    response = SecurityHealthResponse(**health_status)
    
    # Return appropriate HTTP status based on overall status
    if health_status["overall_status"] == "critical":
        # Return 503 (Service Unavailable) for critical issues
        return Response(
            content=response.model_dump_json(),
            status_code=503,
            media_type="application/json"
        )
    elif health_status["overall_status"] == "unhealthy":
        # Return 503 for unhealthy status
        return Response(
            content=response.model_dump_json(),
            status_code=503,
            media_type="application/json"
        )
    elif health_status["overall_status"] == "degraded":
        # Return 200 but with degraded status in body
        return response
    else:
        # Return 200 for healthy status
        return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

