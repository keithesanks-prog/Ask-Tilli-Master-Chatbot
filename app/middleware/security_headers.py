"""
Security Headers Middleware

Provides security headers including HSTS, content security policy, and TLS enforcement.
"""
import os
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers and enforce HTTPS.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        enforce_https: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
    ):
        """
        Initialize security headers middleware.
        
        Args:
            app: ASGI application
            enforce_https: Whether to enforce HTTPS (redirect HTTP to HTTPS)
            hsts_max_age: HSTS max-age in seconds (default: 1 year)
            hsts_include_subdomains: Include subdomains in HSTS
            hsts_preload: Enable HSTS preload
        """
        super().__init__(app)
        self.enforce_https = enforce_https
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and add security headers.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response with security headers
        """
        # Check if HTTPS is required and enforce it
        if self.enforce_https and request.url.scheme == "http":
            # Check if this is not localhost (allow HTTP for local development)
            if request.url.hostname not in ["localhost", "127.0.0.1", "0.0.0.0"]:
                logger.warning(f"HTTP request blocked, redirecting to HTTPS: {request.url}")
                # Return redirect to HTTPS
                https_url = request.url.replace(scheme="https")
                from fastapi.responses import RedirectResponse
                return RedirectResponse(
                    url=str(https_url),
                    status_code=301,  # Permanent redirect
                    headers={"Strict-Transport-Security": self._build_hsts_header()}
                )
        
        # Process the request
        response = await call_next(request)
        
        # Add security headers to response
        self._add_security_headers(response)
        
        return response
    
    def _add_security_headers(self, response: Response):
        """
        Add security headers to response.
        
        Args:
            response: FastAPI response
        """
        # HSTS (HTTP Strict Transport Security)
        if self.enforce_https:
            hsts_header = self._build_hsts_header()
            response.headers["Strict-Transport-Security"] = hsts_header
        
        # Content Security Policy
        # Allow Swagger UI/CDN assets so /docs renders (cdn.jsdelivr.net, unpkg.com)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' https://generativelanguage.googleapis.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # X-Content-Type-Options: Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection: Enable XSS filter (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy: Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy: Disable unnecessary browser features
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy
        
        # Remove server-identifying headers where possible
        try:
            if "Server" in response.headers:
                del response.headers["Server"]
        except Exception:
            # Some response types may not allow deletion; ignore silently
            pass
        
        try:
            if "X-Powered-By" in response.headers:
                del response.headers["X-Powered-By"]
        except Exception:
            pass
    
    def _build_hsts_header(self) -> str:
        """
        Build HSTS header string.
        
        Returns:
            HSTS header value
        """
        parts = [f"max-age={self.hsts_max_age}"]
        
        if self.hsts_include_subdomains:
            parts.append("includeSubDomains")
        
        if self.hsts_preload:
            parts.append("preload")
        
        return "; ".join(parts)


class TLSEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce TLS/HTTPS connections.
    """
    
    def __init__(self, app: ASGIApp, require_tls: bool = True, allowed_hosts: list = None):
        """
        Initialize TLS enforcement middleware.
        
        Args:
            app: ASGI application
            require_tls: Whether to require TLS
            allowed_hosts: List of allowed hostnames (for Host header validation)
        """
        super().__init__(app)
        self.require_tls = require_tls
        self.allowed_hosts = allowed_hosts or []
        # Allow localhost for development
        if not self.allowed_hosts:
            self.allowed_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate TLS.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response or error if TLS required but not present
        """
        # Check TLS requirement
        if self.require_tls:
            # Check if request is over HTTPS
            # In production, check X-Forwarded-Proto header (set by reverse proxy)
            is_https = (
                request.url.scheme == "https" or
                request.headers.get("X-Forwarded-Proto") == "https" or
                request.headers.get("X-Forwarded-Ssl") == "on"
            )
            
            # Allow HTTP for localhost in development
            is_localhost = request.url.hostname in ["localhost", "127.0.0.1", "0.0.0.0"]
            
            if not is_https and not is_localhost:
                from fastapi import HTTPException
                logger.warning(f"TLS required but request is not over HTTPS: {request.url}")
                raise HTTPException(
                    status_code=400,
                    detail="TLS/HTTPS is required for this endpoint"
                )
            
            # Validate Host header if allowed_hosts is configured
            if self.allowed_hosts and request.url.hostname:
                if request.url.hostname not in self.allowed_hosts:
                    from fastapi import HTTPException
                    logger.warning(f"Invalid host header: {request.url.hostname}")
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid host header"
                    )
        
        # Process the request
        response = await call_next(request)
        return response


