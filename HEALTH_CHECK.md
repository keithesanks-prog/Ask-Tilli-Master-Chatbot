# Security Health Check Endpoint

**Document Version:** 1.1  
**Last Updated:** 2025-11-23  
**Purpose:** Validate that all security countermeasures are active and functioning

---

## Overview

The Security Health Check endpoint (`/health/security`) provides comprehensive validation of all security countermeasures to ensure the service is properly protected and compliant with FERPA, UNICEF, and other regulatory requirements.

**Recent Updates:**
- ✅ Auth0 integration checks added
- ✅ Data access control validation added
- ✅ School-level isolation checks added

---

## Endpoint

**GET `/health/security`**

**Rate Limit:** 10 requests per minute

**Authentication:** Optional (can be used for monitoring without auth)

---

## What Is Checked

### ✅ **1. Service Status**
- Service is running
- Version information

### ✅ **2. Transport Security**
- TLS/HTTPS enforcement enabled
- Security headers configured
- Production vs. development environment

**Issues Detected:**
- TLS not enforced in production
- HTTPS not enforced in production

---

### ✅ **3. Authentication**
- Authentication enabled (production check)
- **Auth0 configuration** (if Auth0 mode)
  - Auth0 domain configured
  - Auth0 audience configured
  - JWKS endpoint accessible
- **Local JWT configuration** (if local dev mode)
  - JWT secret key configured
- Authentication middleware active
- Hybrid mode status

**Issues Detected:**
- Authentication not enabled in production (CRITICAL)
- Auth0 not configured in production (WARNING)
- JWT secret key not configured (local dev mode)

---

### ✅ **4. Rate Limiting**
- Rate limiter initialized
- Rate limits configured
- Per-endpoint limits active

**Details:**
- Shows all configured rate limits
- Verifies rate limiter is active

---

### ✅ **5. Input Validation**
- Input sanitizer available
- Prompt injection patterns configured
- SQL injection patterns configured
- Pattern detection working

**Details:**
- Number of patterns per type
- Test that sanitization works

---

### ✅ **6. Harmful Content Detection**
- Harmful content detector available
- Detector enabled
- Pattern matching working

**Details:**
- Detector status
- Pattern types available
- Test that detection works

---

### ✅ **7. Audit Logging**
- Audit logger available
- Audit logger enabled
- Logging configuration (file/stdout)
- Log file configured (if applicable)

**Details:**
- Logging destinations
- Log file path (if configured)

---

### ✅ **8. External API (Gemini)**
- API key configured
- Connectivity status
- Fallback available (mock responses)

**Status:**
- `configured` - API key set and configured
- `not_installed` - Gemini SDK not installed
- `error` - Configuration error
- `unknown` - Status unknown

---

### ✅ **9. Security Headers**
- Security headers middleware active
- HTTPS enforcement
- HSTS configuration

**Details:**
- HSTS max-age
- Production mode status

---

### ✅ **10. CORS Configuration**
- CORS middleware configured
- Allowed origins configured
- Production safety checks

**Issues Detected:**
- CORS allows all origins in production

---

### ✅ **11. Data Access Control** 🆕

- **School-level isolation** enabled
- Cross-school access prevention active
- Access control logic implemented
- Audit logging of access attempts

**Details:**
- School isolation status
- Access control middleware active
- Test that cross-school access is blocked

**Issues Detected:**
- Data access control not enabled in production (CRITICAL)
- School isolation not configured

---

## Response Format

### **Overall Status Levels**

1. **`healthy`** - All security measures functioning properly
2. **`degraded`** - Some security measures have issues (non-critical)
3. **`unhealthy`** - Critical security measures are not functioning
4. **`critical`** - Major security vulnerabilities present

### **HTTP Status Codes**

- **`200 OK`** - Service is healthy or degraded (check `overall_status` in response)
- **`503 Service Unavailable`** - Service is unhealthy or critical issues present

---

## Example Response

### **Healthy Status (200 OK)**

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "overall_status": "healthy",
  "service_version": "0.1.0",
  "checks": {
    "service": {
      "status": "healthy",
      "message": "Service is running",
      "details": {
        "service_name": "Master Agent API",
        "version": "0.1.0"
      }
    },
    "transport_security": {
      "status": "healthy",
      "message": "TLS/HTTPS configuration checked",
      "details": {
        "environment": "production",
        "tls_enforced": true,
        "https_enforced": true,
        "production_mode": true,
        "issues": []
      }
    },
    "authentication": {
      "status": "healthy",
      "message": "Authentication configuration checked",
      "details": {
        "authentication_enabled": true,
        "jwt_secret_configured": true,
        "production_mode": true,
        "issues": []
      }
    },
    "rate_limiting": {
      "status": "healthy",
      "message": "Rate limiting is configured",
      "details": {
        "rate_limiter_initialized": true,
        "rate_limits_configured": true,
        "configured_limits": {
          "ask": "10/minute",
          "query": "30/minute",
          "prompt_eval": "5/minute",
          "health": "100/minute"
        }
      }
    },
    "input_validation": {
      "status": "healthy",
      "message": "Input validation is active",
      "details": {
        "input_sanitizer_available": true,
        "prompt_injection_patterns": true,
        "sql_injection_patterns": true,
        "pattern_count": {
          "prompt_injection": 20,
          "sql_injection": 7
        },
        "test_passed": true
      }
    },
    "harmful_content_detection": {
      "status": "healthy",
      "message": "Harmful content detection is active",
      "details": {
        "detector_available": true,
        "detector_enabled": true,
        "test_passed": true,
        "pattern_types": 13
      }
    },
    "audit_logging": {
      "status": "healthy",
      "message": "Audit logging is configured",
      "details": {
        "audit_logger_available": true,
        "audit_logger_enabled": true,
        "log_to_file": false,
        "log_to_stdout": true,
        "log_file": null
      }
    },
    "external_api": {
      "status": "healthy",
      "message": "External API (Gemini) configuration checked",
      "details": {
        "api_key_configured": true,
        "connectivity_status": "configured",
        "fallback_available": true
      }
    },
    "security_headers": {
      "status": "healthy",
      "message": "Security headers middleware is configured",
      "details": {
        "security_headers_available": true,
        "https_enforced": true,
        "hsts_max_age": 31536000,
        "production_mode": true
      }
    },
    "cors": {
      "status": "healthy",
      "message": "CORS configuration checked",
      "details": {
        "allowed_origins_count": 2,
        "allows_all_origins": false,
        "production_mode": true,
        "issues": []
      }
    }
  },
  "summary": {
    "total_checks": 10,
    "healthy": 10,
    "degraded": 0,
    "unhealthy": 0,
    "critical": 0,
    "issues": [],
    "overall_status": "healthy"
  }
}
```

---

### **Degraded Status (200 OK with degraded status)**

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "overall_status": "degraded",
  "service_version": "0.1.0",
  "checks": {
    "authentication": {
      "status": "degraded",
      "message": "Authentication configuration checked",
      "details": {
        "authentication_enabled": false,
        "jwt_secret_configured": false,
        "production_mode": true,
        "issues": ["Authentication not enabled in production"]
      }
    },
    ...
  },
  "summary": {
    "total_checks": 10,
    "healthy": 9,
    "degraded": 1,
    "unhealthy": 0,
    "critical": 0,
    "issues": [
      {
        "check": "authentication",
        "status": "degraded",
        "message": "Authentication configuration checked",
        "issues": ["Authentication not enabled in production"]
      }
    ],
    "overall_status": "degraded"
  }
}
```

---

### **Critical/Unhealthy Status (503 Service Unavailable)**

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "overall_status": "critical",
  "service_version": "0.1.0",
  "checks": {
    "authentication": {
      "status": "critical",
      "message": "Authentication configuration checked",
      "details": {
        "authentication_enabled": false,
        "jwt_secret_configured": false,
        "production_mode": true,
        "issues": ["Authentication not enabled in production"]
      }
    },
    ...
  },
  "summary": {
    "total_checks": 10,
    "healthy": 8,
    "degraded": 0,
    "unhealthy": 1,
    "critical": 1,
    "issues": [
      {
        "check": "authentication",
        "status": "critical",
        "message": "Authentication configuration checked",
        "issues": ["Authentication not enabled in production"]
      }
    ],
    "overall_status": "critical"
  }
}
```

---

## Use Cases

### **1. Monitoring & Alerting**

**Automated Monitoring:**
```bash
# Check security health every minute
while true; do
  status=$(curl -s https://api.example.com/health/security | jq -r '.overall_status')
  if [ "$status" != "healthy" ]; then
    # Send alert
    echo "Security health check failed: $status"
    # Send to monitoring system (PagerDuty, Datadog, etc.)
  fi
  sleep 60
done
```

**Monitoring Integration:**
- **Datadog** - Create monitor on `/health/security` endpoint
- **PagerDuty** - Alert on 503 status codes
- **Prometheus** - Scrape health endpoint and expose metrics
- **Nagios** - Check endpoint and alert on failures

---

### **2. Deployment Verification**

**Post-Deployment Check:**
```bash
# After deployment, verify security measures are active
curl https://api.example.com/health/security | jq '.summary'

# Exit with error if not healthy
status=$(curl -s https://api.example.com/health/security | jq -r '.overall_status')
if [ "$status" != "healthy" ]; then
  echo "Security health check failed after deployment"
  exit 1
fi
```

---

### **3. Incident Response**

**Quick Diagnosis:**
```bash
# Check which security measures are failing
curl https://api.example.com/health/security | jq '.summary.issues'

# Output:
# [
#   {
#     "check": "authentication",
#     "status": "critical",
#     "message": "Authentication configuration checked",
#     "issues": ["Authentication not enabled in production"]
#   }
# ]
```

---

### **4. Compliance Audits**

**UNICEF/FERPA Compliance Verification:**
```bash
# Verify all security measures are active
curl https://api.example.com/health/security | jq '{
  overall_status,
  security_checks: .checks | {
    audit_logging: .audit_logging.status,
    harmful_content_detection: .harmful_content_detection.status,
    input_validation: .input_validation.status,
    transport_security: .transport_security.status
  }
}'
```

---

### **5. Health Dashboard**

**Real-Time Dashboard:**
```python
# Display security health in dashboard
import requests

response = requests.get("https://api.example.com/health/security")
health = response.json()

print(f"Overall Status: {health['overall_status']}")
print(f"Healthy Checks: {health['summary']['healthy']}/{health['summary']['total_checks']}")
print(f"Issues: {len(health['summary']['issues'])}")

for issue in health['summary']['issues']:
    print(f"  - {issue['check']}: {issue['status']} - {issue['issues']}")
```

---

## Integration Examples

### **Prometheus Metrics**

Expose health check as Prometheus metrics:

```python
# Scrape /health/security and expose metrics
security_health_status = Gauge(
    'security_health_status',
    'Security health status (0=healthy, 1=degraded, 2=unhealthy, 3=critical)'
)

security_checks_healthy = Gauge(
    'security_checks_healthy',
    'Number of healthy security checks',
    ['check_name']
)
```

---

### **Datadog Monitor**

Create Datadog monitor:

```yaml
- name: Security Health Check
  type: service check
  query: |
    http_check("https://api.example.com/health/security")
  alert:
    condition: |
      status != "ok"
    message: |
      Security health check failed. Check /health/security for details.
```

---

### **PagerDuty Integration**

Alert on critical issues:

```python
# If overall_status is "critical" or "unhealthy", send to PagerDuty
if health_status["overall_status"] in ["critical", "unhealthy"]:
    pagerduty.trigger_incident(
        title="Security Health Check Failed",
        description=f"Status: {health_status['overall_status']}",
        details=health_status["summary"]["issues"]
    )
```

---

## Best Practices

### **1. Regular Monitoring**
- Check `/health/security` every 1-5 minutes
- Alert on status changes (healthy → degraded/unhealthy/critical)
- Log health check results for trending

### **2. Automated Remediation**
- Automatically fix common issues (if possible)
- Alert on issues that require manual intervention
- Document remediation procedures

### **3. Dashboard Display**
- Show security health status in operations dashboard
- Display individual check statuses
- Show trends over time

### **4. Compliance Reporting**
- Include security health status in compliance reports
- Document any degraded/unhealthy periods
- Explain remediation steps taken

---

## Troubleshooting

### **Common Issues**

#### **1. Authentication Not Enabled in Production**
```
Issue: "Authentication not enabled in production"
Fix: Set ENABLE_AUTH=true environment variable
```

#### **2. TLS Not Enforced in Production**
```
Issue: "TLS not enforced in production"
Fix: Set REQUIRE_TLS=true or ENVIRONMENT=production
```

#### **3. Gemini API Not Configured**
```
Issue: External API status is "degraded"
Fix: Set GEMINI_API_KEY environment variable (optional - service works with mock responses)
```

#### **4. CORS Allows All Origins in Production**
```
Issue: "CORS allows all origins in production"
Fix: Set ALLOWED_ORIGINS to specific origins, remove "*"
```

---

## Security Considerations

### **Access Control**

**Public Access:**
- ✅ Health endpoint can be accessed without authentication (for monitoring)
- ⚠️ Consider restricting `/health/security` in production (more sensitive)
- ⚠️ Use IP whitelisting for security endpoint (if needed)

**Recommended:**
```python
# Restrict security endpoint to internal IPs or monitoring systems
@app.get("/health/security")
@limiter.limit("10/minute")
async def security_health_check(request: Request):
    # Check if request is from allowed IP
    client_ip = request.client.host
    if client_ip not in ALLOWED_MONITORING_IPS:
        raise HTTPException(403, "Forbidden")
    # ... rest of check
```

---

## Examples

### **Command Line**

```bash
# Basic check
curl https://api.example.com/health/security

# Pretty print
curl -s https://api.example.com/health/security | jq '.'

# Check overall status only
curl -s https://api.example.com/health/security | jq -r '.overall_status'

# List all issues
curl -s https://api.example.com/health/security | jq '.summary.issues'

# Check specific security measure
curl -s https://api.example.com/health/security | jq '.checks.authentication'
```

---

### **Python Script**

```python
import requests
import json

def check_security_health():
    """Check security health and alert on issues."""
    response = requests.get("https://api.example.com/health/security")
    health = response.json()
    
    overall_status = health["overall_status"]
    summary = health["summary"]
    
    print(f"Security Health Status: {overall_status}")
    print(f"Healthy: {summary['healthy']}/{summary['total_checks']}")
    print(f"Degraded: {summary['degraded']}")
    print(f"Unhealthy: {summary['unhealthy']}")
    print(f"Critical: {summary['critical']}")
    
    if summary["issues"]:
        print("\nIssues Found:")
        for issue in summary["issues"]:
            print(f"  - {issue['check']}: {issue['status']}")
            for i in issue.get('issues', []):
                print(f"    • {i}")
    
    return overall_status

if __name__ == "__main__":
    status = check_security_health()
    exit(0 if status == "healthy" else 1)
```

---

### **Monitoring Script (Cron Job)**

```bash
#!/bin/bash
# Security health check monitoring script
# Run every 5 minutes via cron

API_URL="https://api.example.com/health/security"
ALERT_EMAIL="security@example.com"

# Check health status
STATUS=$(curl -s "$API_URL" | jq -r '.overall_status')
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL")

# Alert on critical/unhealthy status or 503 response
if [ "$HTTP_CODE" = "503" ] || [ "$STATUS" = "critical" ] || [ "$STATUS" = "unhealthy" ]; then
    echo "Security health check failed: $STATUS (HTTP $HTTP_CODE)" | \
    mail -s "Security Alert: Health Check Failed" "$ALERT_EMAIL"
fi
```

---

## API Reference

**Endpoint:** `GET /health/security`

**Response Model:** `SecurityHealthResponse`

**Rate Limit:** 10 requests per minute

**Authentication:** Optional

**HTTP Status Codes:**
- `200 OK` - Healthy or Degraded
- `503 Service Unavailable` - Unhealthy or Critical

---

## References

- [FastAPI Health Checks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Monitoring Best Practices](https://docs.datadoghq.com/monitors/)
- [Prometheus Health Checks](https://prometheus.io/docs/practices/instrumentation/)

---

**Document Version:** 1.0  
**Last Updated:** 2024


