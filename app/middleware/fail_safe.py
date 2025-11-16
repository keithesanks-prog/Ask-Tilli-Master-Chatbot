"""
Fail-Safe Middleware

Implements fail-safe behavior: rejects new requests when service is stopping.
Ensures that when service stops, no new actions are allowed (like a safe lock).
"""
import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..services.service_manager import get_service_manager

logger = logging.getLogger(__name__)


class FailSafeMiddleware(BaseHTTPMiddleware):
    """
    Fail-safe middleware that rejects new requests when service is stopping.
    
    Fail-Safe Behavior:
    - When service is STOPPING, all new requests are rejected with 503
    - Prevents new data access during shutdown
    - Ensures no partial state during shutdown
    - Like a safe lock that locks when power fails
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with fail-safe check.
        
        If service is stopping, reject request immediately.
        If service is running, allow request and track it.
        """
        service_manager = get_service_manager()
        
        # Fail-safe: Check if service is accepting requests
        if not service_manager.is_accepting_requests:
            logger.warning(
                f"Request rejected (fail-safe): Service is {service_manager.state.value}. "
                f"URL: {request.url.path}"
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable",
                    "message": "Service is shutting down. Please try again later.",
                    "service_state": service_manager.state.value,
                    "fail_safe": True
                }
            )
        
        # Enter request (track in-flight requests)
        if not service_manager.enter_request():
            # Service entered stopping state between check and enter
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable",
                    "message": "Service is shutting down. Please try again later.",
                    "service_state": service_manager.state.value,
                    "fail_safe": True
                }
            )
        
        try:
            # Process request
            response = await call_next(request)
            return response
        finally:
            # Exit request (mark as complete)
            service_manager.exit_request()


