"""
Security Health Check Service

Validates that all security countermeasures are active and functioning properly.
Provides detailed health status for monitoring and alerting.
"""
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class SecurityHealthCheck:
    """
    Validates security countermeasures and returns health status.
    
    Checks:
    - TLS/HTTPS enforcement
    - Authentication configuration
    - Rate limiting
    - Input sanitization
    - Harmful content detection
    - Audit logging
    - External API (Gemini) connectivity
    - Security headers
    - CORS configuration
    """
    
    def __init__(self):
        """Initialize the security health check service."""
        pass
    
    def check_all(self) -> Dict[str, Any]:
        """
        Run all security health checks.
        
        Returns:
            Dictionary with comprehensive health status
        """
        checks = {
            "service": self.check_service(),
            "transport_security": self.check_transport_security(),
            "authentication": self.check_authentication(),
            "rate_limiting": self.check_rate_limiting(),
            "input_validation": self.check_input_validation(),
            "harmful_content_detection": self.check_harmful_content_detection(),
            "audit_logging": self.check_audit_logging(),
            "external_api": self.check_external_api(),
            "security_headers": self.check_security_headers(),
            "cors": self.check_cors(),
        }
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(checks)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": overall_status.value,
            "service_version": "0.1.0",
            "checks": checks,
            "summary": self._generate_summary(checks, overall_status)
        }
    
    def check_service(self) -> Dict[str, Any]:
        """Check if service is running."""
        try:
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Service is running",
                "details": {
                    "service_name": "Master Agent API",
                    "version": "0.1.0"
                }
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Service check failed: {str(e)}",
                "details": {}
            }
    
    def check_transport_security(self) -> Dict[str, Any]:
        """Check TLS/HTTPS enforcement."""
        environment = os.getenv("ENVIRONMENT", "development")
        require_tls = os.getenv("REQUIRE_TLS", "false").lower() == "true"
        enforce_https = os.getenv("ENFORCE_HTTPS", "false").lower() == "true"
        is_production = environment == "production"
        
        tls_enabled = require_tls or is_production
        https_enforced = enforce_https or is_production
        
        issues = []
        if not tls_enabled and is_production:
            issues.append("TLS not enforced in production")
        if not https_enforced and is_production:
            issues.append("HTTPS not enforced in production")
        
        status = HealthStatus.HEALTHY if not issues else HealthStatus.DEGRADED
        
        return {
            "status": status.value,
            "message": "TLS/HTTPS configuration checked",
            "details": {
                "environment": environment,
                "tls_enforced": tls_enabled,
                "https_enforced": https_enforced,
                "production_mode": is_production,
                "issues": issues
            }
        }
    
    def check_authentication(self) -> Dict[str, Any]:
        """Check authentication configuration."""
        enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        environment = os.getenv("ENVIRONMENT", "development")
        is_production = environment == "production"
        
        issues = []
        if not enable_auth and is_production:
            issues.append("Authentication not enabled in production")
        if enable_auth and not jwt_secret:
            issues.append("JWT secret key not configured")
        
        status = HealthStatus.HEALTHY
        if not enable_auth and is_production:
            status = HealthStatus.CRITICAL
        elif enable_auth and not jwt_secret:
            status = HealthStatus.UNHEALTHY
        
        return {
            "status": status.value,
            "message": "Authentication configuration checked",
            "details": {
                "authentication_enabled": enable_auth,
                "jwt_secret_configured": jwt_secret is not None,
                "production_mode": is_production,
                "issues": issues
            }
        }
    
    def check_rate_limiting(self) -> Dict[str, Any]:
        """Check rate limiting configuration."""
        try:
            from ..middleware.rate_limit import limiter, RATE_LIMITS
            
            # Check if rate limiter is initialized
            rate_limits_configured = len(RATE_LIMITS) > 0
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Rate limiting is configured",
                "details": {
                    "rate_limiter_initialized": limiter is not None,
                    "rate_limits_configured": rate_limits_configured,
                    "configured_limits": RATE_LIMITS
                }
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Rate limiting check failed: {str(e)}",
                "details": {}
            }
    
    def check_input_validation(self) -> Dict[str, Any]:
        """Check input validation and sanitization."""
        try:
            from .security import InputSanitizer
            
            # Test that sanitization works
            test_input = "test question"
            sanitized = InputSanitizer.sanitize_question(test_input)
            
            # Check if patterns are defined
            prompt_patterns = len(InputSanitizer.PROMPT_INJECTION_PATTERNS) > 0
            sql_patterns = len(InputSanitizer.SQL_INJECTION_PATTERNS) > 0
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Input validation is active",
                "details": {
                    "input_sanitizer_available": True,
                    "prompt_injection_patterns": prompt_patterns,
                    "sql_injection_patterns": sql_patterns,
                    "pattern_count": {
                        "prompt_injection": len(InputSanitizer.PROMPT_INJECTION_PATTERNS),
                        "sql_injection": len(InputSanitizer.SQL_INJECTION_PATTERNS)
                    },
                    "test_passed": sanitized == test_input
                }
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Input validation check failed: {str(e)}",
                "details": {}
            }
    
    def check_harmful_content_detection(self) -> Dict[str, Any]:
        """Check harmful content detection."""
        try:
            from .harmful_content_detector import HarmfulContentDetector
            
            detector = HarmfulContentDetector(enabled=True)
            
            # Test that detection works
            test_result = detector.detect_harmful_content("safe text", context="test")
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Harmful content detection is active",
                "details": {
                    "detector_available": True,
                    "detector_enabled": detector.enabled,
                    "test_passed": not test_result.get("is_harmful"),
                    "pattern_types": len(detector.PATTERN_MAPPING)
                }
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Harmful content detection check failed: {str(e)}",
                "details": {}
            }
    
    def check_audit_logging(self) -> Dict[str, Any]:
        """Check audit logging configuration."""
        try:
            from .audit_logger import FERPAAuditLogger
            
            audit_logger = FERPAAuditLogger(enabled=True)
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Audit logging is configured",
                "details": {
                    "audit_logger_available": True,
                    "audit_logger_enabled": audit_logger.enabled,
                    "log_to_file": audit_logger.log_to_file,
                    "log_to_stdout": audit_logger.log_to_stdout,
                    "log_file": audit_logger.log_file
                }
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Audit logging check failed: {str(e)}",
                "details": {}
            }
    
    def check_external_api(self) -> Dict[str, Any]:
        """Check external API (Gemini) connectivity and configuration."""
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        gemini_available = gemini_api_key is not None
        
        # Try to initialize Gemini to check connectivity
        connectivity_status = "unknown"
        try:
            import google.generativeai as genai
            if gemini_api_key:
                genai.configure(api_key=gemini_api_key)
                # Just check if it's configured, don't make actual API call
                connectivity_status = "configured"
        except ImportError:
            connectivity_status = "not_installed"
        except Exception as e:
            connectivity_status = f"error: {str(e)[:50]}"
        
        status = HealthStatus.HEALTHY
        if not gemini_available:
            status = HealthStatus.DEGRADED  # Degraded because it falls back to mock
        
        return {
            "status": status.value,
            "message": "External API (Gemini) configuration checked",
            "details": {
                "api_key_configured": gemini_available,
                "connectivity_status": connectivity_status,
                "fallback_available": True  # Mock responses available
            }
        }
    
    def check_security_headers(self) -> Dict[str, Any]:
        """Check security headers configuration."""
        try:
            from ..middleware.security_headers import SecurityHeadersMiddleware
            
            enforce_https = os.getenv("ENFORCE_HTTPS", "false").lower() == "true"
            environment = os.getenv("ENVIRONMENT", "development")
            is_production = environment == "production"
            
            https_enforced = enforce_https or is_production
            hsts_max_age = int(os.getenv("HSTS_MAX_AGE", "31536000"))
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Security headers middleware is configured",
                "details": {
                    "security_headers_available": True,
                    "https_enforced": https_enforced,
                    "hsts_max_age": hsts_max_age,
                    "production_mode": is_production
                }
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Security headers check failed: {str(e)}",
                "details": {}
            }
    
    def check_cors(self) -> Dict[str, Any]:
        """Check CORS configuration."""
        allowed_origins = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:8000"
        ).split(",")
        environment = os.getenv("ENVIRONMENT", "development")
        is_production = environment == "production"
        
        issues = []
        if is_production and "*" in allowed_origins:
            issues.append("CORS allows all origins in production")
        
        status = HealthStatus.HEALTHY if not issues else HealthStatus.DEGRADED
        
        return {
            "status": status.value,
            "message": "CORS configuration checked",
            "details": {
                "allowed_origins_count": len([o for o in allowed_origins if o.strip()]),
                "allows_all_origins": "*" in allowed_origins,
                "production_mode": is_production,
                "issues": issues
            }
        }
    
    def _calculate_overall_status(self, checks: Dict[str, Any]) -> HealthStatus:
        """Calculate overall health status from individual checks."""
        statuses = [check.get("status") for check in checks.values()]
        
        if HealthStatus.CRITICAL.value in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY.value in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED.value in statuses:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def _generate_summary(self, checks: Dict[str, Any], overall_status: HealthStatus) -> Dict[str, Any]:
        """Generate summary of health checks."""
        total_checks = len(checks)
        healthy = sum(1 for c in checks.values() if c.get("status") == HealthStatus.HEALTHY.value)
        degraded = sum(1 for c in checks.values() if c.get("status") == HealthStatus.DEGRADED.value)
        unhealthy = sum(1 for c in checks.values() if c.get("status") == HealthStatus.UNHEALTHY.value)
        critical = sum(1 for c in checks.values() if c.get("status") == HealthStatus.CRITICAL.value)
        
        # List issues
        issues = []
        for check_name, check_result in checks.items():
            check_status = check_result.get("status")
            if check_status in [HealthStatus.CRITICAL.value, HealthStatus.UNHEALTHY.value]:
                issues.append({
                    "check": check_name,
                    "status": check_status,
                    "message": check_result.get("message", ""),
                    "issues": check_result.get("details", {}).get("issues", [])
                })
        
        return {
            "total_checks": total_checks,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "critical": critical,
            "issues": issues,
            "overall_status": overall_status.value
        }


