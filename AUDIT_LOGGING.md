# Audit Logging System

**Document Version:** 1.0  
**Last Updated:** 2024  
**FERPA & UNICEF Compliance**

---

## Overview

The Audit Logging System provides comprehensive, FERPA and UNICEF-compliant logging of all data access, security events, and harmful content detections.

**Purpose:** To maintain an immutable audit trail of all system activity for compliance with FERPA, UNICEF, GDPR, and COPPA requirements.

---

## Why Audit Logging Is Required

### **FERPA Compliance** 🔴 **CRITICAL**

**Requirements:**
- ✅ Must log ALL access to student records
- ✅ Must track who accessed what data
- ✅ Must maintain audit trail for compliance
- ✅ Must be tamper-proof
- ✅ Must support 7-year retention

**What Must Be Logged:**
- Every data access (who, what, when)
- User identity (user_id, email, role)
- Data accessed (student_id, classroom_id, data_sources)
- Purpose of access (why data was accessed)
- IP address and session information

---

### **UNICEF Compliance** 🔴 **CRITICAL**

**Requirements:**
- ✅ Must log ALL access to child data (even more comprehensive than FERPA)
- ✅ Must track purpose of access (why data was accessed)
- ✅ Must maintain immutable audit trail
- ✅ Must be tamper-proof and append-only
- ✅ Must include child protection context in logs
- ✅ Must support UNICEF audits

**What Must Be Logged:**
- Every data access with purpose tracking
- Harmful content detections (child safety concerns)
- Security events related to child data
- PII exposure events
- Data misuse attempts

---

### **GDPR & COPPA Compliance**

**Requirements:**
- ✅ Must log all data access for GDPR compliance
- ✅ Must track data subject rights requests
- ✅ Must support COPPA compliance (children under 13)
- ✅ Must maintain audit trail for regulatory compliance

---

## What Is Logged

### **1. Data Access Events** ✅ **IMPLEMENTED**

**Logged for every data access:**

- **Who:** user_id, user_email, user_role
- **What:** student_id, classroom_id, data_sources (REAL, EMT, SEL)
- **When:** timestamp (UTC)
- **Why:** purpose (UNICEF requirement - why data was accessed)
- **Where:** school_id (tenant), ip_address, session_id
- **Action:** action type ("view", "query", "export")

**Example:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "event_type": "data_access",
  "severity": "low",
  "user_id": "user_123",
  "user_email": "educator@school.edu",
  "user_role": "educator",
  "school_id": "school_456",
  "action": "query",
  "purpose": "Educational inquiry - analyzing student assessment data",
  "student_id": "student_789",
  "classroom_id": "classroom_001",
  "grade_level": "Grade 3",
  "question_length": 45,
  "data_sources": ["REAL", "EMT", "SEL"],
  "ip_address": "192.168.1.100",
  "session_id": "session_abc123",
  "compliance_flags": {
    "ferpa": true,
    "unicef": true,
    "gdpr": true,
    "coppa": true
  },
  "metadata": {
    "confidence": "high",
    "response_length": 250,
    "data_sources_count": 3
  }
}
```

---

### **2. Harmful Content Detection Events** ✅ **IMPLEMENTED**

**Logged for every harmful content detection:**

- **Who:** user_id, user_email
- **What:** harm_types, severity, context ("question" or "response")
- **When:** timestamp (UTC)
- **Why:** Harmful content detected (child safety concern)
- **Where:** school_id, student_id (if applicable), ip_address
- **Details:** matches_count, text_preview (first 200 chars, no PII)

**Example:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "event_type": "harmful_content",
  "severity": "critical",
  "user_id": "user_123",
  "user_email": "educator@school.edu",
  "school_id": "school_456",
  "harm_types": ["self_harm", "suicidal_ideation"],
  "context": "question",
  "student_id": "student_789",
  "matches_count": 2,
  "text_preview": "Student mentioned wanting to end their life...",
  "ip_address": "192.168.1.100",
  "session_id": "session_abc123",
  "compliance_flags": {
    "ferpa": true,
    "unicef": true,
    "gdpr": true,
    "coppa": true
  },
  "requires_immediate_action": true,
  "unicef_aligned": true,
  "metadata": {
    "alert": {...}
  }
}
```

---

### **3. Security Events** ✅ **IMPLEMENTED**

**Logged for security events:**

- Authentication events
- Authorization failures
- Rate limit violations
- Security violations
- System access attempts

**Example:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "event_type": "security_event",
  "severity": "high",
  "user_id": "user_123",
  "user_email": "educator@school.edu",
  "school_id": "school_456",
  "security_event_type": "unauthorized_access",
  "description": "Attempted access to different school's data",
  "ip_address": "192.168.1.100",
  "session_id": "session_abc123",
  "compliance_flags": {
    "ferpa": true,
    "unicef": true,
    "gdpr": true,
    "coppa": false
  },
  "metadata": {}
}
```

---

### **4. PII Exposure Events** ✅ **IMPLEMENTED**

**Logged for PII exposure detection:**

- PII entity types detected
- Context where PII was detected
- Number of PII entities
- User and school context

**Example:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "event_type": "pii_exposure",
  "severity": "high",
  "user_id": "user_123",
  "user_email": "educator@school.edu",
  "school_id": "school_456",
  "context": "response",
  "pii_entity_types": ["PERSON", "EMAIL_ADDRESS"],
  "pii_entities_count": 3,
  "student_id": "student_789",
  "ip_address": "192.168.1.100",
  "session_id": "session_abc123",
  "compliance_flags": {
    "ferpa": true,
    "unicef": true,
    "gdpr": true,
    "coppa": true
  },
  "requires_immediate_action": true,
  "metadata": {}
}
```

---

## Implementation

### **Location**

- **Service:** `app/services/audit_logger.py`
- **Class:** `FERPAAuditLogger`

### **Integration**

**Agent Router Integration:**
- ✅ Logs data access for every `/agent/ask` request
- ✅ Logs harmful content detections (questions and responses)
- ✅ Includes full context (user, school, student, purpose)

**Usage Example:**
```python
from app.services.audit_logger import FERPAAuditLogger

audit_logger = FERPAAuditLogger(enabled=True)

# Log data access
audit_logger.log_data_access(
    user_id="user_123",
    user_email="educator@school.edu",
    user_role="educator",
    school_id="school_456",
    action="query",
    purpose="Educational inquiry - analyzing student assessment data",
    student_id="student_789",
    data_sources_accessed=["REAL", "EMT", "SEL"],
    ip_address="192.168.1.100"
)

# Log harmful content
audit_logger.log_harmful_content(
    user_id="user_123",
    user_email="educator@school.edu",
    school_id="school_456",
    severity="critical",
    harm_types=["self_harm"],
    context="question",
    student_id="student_789"
)
```

---

## Audit Log Storage

### **Current Implementation**

**Development/Testing:**
- ✅ Logs to stdout (structured logging)
- ✅ Optional file logging (via `AUDIT_LOG_FILE` environment variable)
- ✅ JSON format for easy parsing

### **Production Requirements**

**Must Use Immutable Storage:**

1. **AWS CloudTrail + S3** (Recommended for AWS)
   - Immutable S3 bucket with versioning
   - Encrypted at rest
   - 7-year retention policy
   - Append-only access

2. **Google Cloud Audit Logs** (Recommended for GCP)
   - Immutable audit logs
   - Encrypted at rest
   - Retention policies
   - Centralized logging

3. **Dedicated Audit Database**
   - Append-only table (no DELETE/UPDATE)
   - Encrypted at rest
   - Regular backups
   - Access controls (read-only for compliance team)

4. **Syslog + Centralized Logging**
   - Immutable syslog server
   - ELK Stack / Splunk
   - Encrypted transport
   - Centralized storage

---

## Configuration

- Pluggable sinks (NEW)

You can forward every audit event to external systems by enabling sinks via environment variables.

Supported sinks:
- Splunk HEC (proprietary, widely used; simple HTTPS JSON)
- Webhook (generic HTTP POST; works with Logstash HTTP input, Vector, Fluent Bit, custom receivers)
- OpenSearch/Elasticsearch (open-source stack)

Configuration:
```
# Enable one or more sinks (comma-separated): splunk,webhook,opensearch
AUDIT_SINKS=splunk,webhook,opensearch

# Splunk HEC (optional)
SPLUNK_HEC_URL=https://splunk.example.com:8088/services/collector
SPLUNK_HEC_TOKEN=<hec-token>
SPLUNK_SOURCE=master-agent
SPLUNK_SOURCETYPE=json
# optional
SPLUNK_INDEX=security

# Webhook (optional)
AUDIT_WEBHOOK_URL=https://log-collector.example.com/ingest
# Optional JSON headers (string)
AUDIT_WEBHOOK_HEADERS={"X-Api-Key":"abc123","X-Source":"master-agent"}

# OpenSearch/Elasticsearch (optional)
OPENSEARCH_URL=https://opensearch.example.com:9200
OPENSEARCH_INDEX=audits
OPENSEARCH_USERNAME=elastic
OPENSEARCH_PASSWORD=<password>
OPENSEARCH_TLS_VERIFY=true

# Networking
AUDIT_HTTP_TIMEOUT=5
AUDIT_HTTP_RETRIES=2
```

Notes:
- Forwarding is fire-and-forget with short timeouts and minimal retries so audits never block request handling.
- Sensitive fields are already minimized; do not include full question texts to avoid PII.
- Keep local stdout/file logging enabled for defense in depth and incident triage.

### **Environment Variables**

```bash
# Enable/disable audit logging
ENABLE_AUDIT_LOGGING=true  # Default: true

# File-based logging (optional, for development)
AUDIT_LOG_FILE=/var/log/master-agent/audit.log

# Enable stdout logging (structured logging)
AUDIT_LOG_STDOUT=true  # Default: true

# Production audit log storage (TODO: future implementation)
AUDIT_LOG_S3_BUCKET=audit-logs-bucket
AUDIT_LOG_S3_PREFIX=master-agent/
AUDIT_LOG_DATABASE_URL=postgresql://...
```

### **Code Configuration**

```python
# Initialize audit logger
audit_logger = FERPAAuditLogger(enabled=True)

# Or disable for testing
audit_logger = FERPAAuditLogger(enabled=False)
```

---

## Compliance Features

### **FERPA Compliance**

✅ **All Data Access Logged** - Every student record access is logged  
✅ **Who, What, When** - Complete audit trail of who accessed what data  
✅ **7-Year Retention** - Logs support 7-year retention requirement  
✅ **Tamper-Proof** - Append-only logging (no deletion/modification)  
✅ **Audit Trail** - Available for FERPA audits  

### **UNICEF Compliance**

✅ **Purpose Tracking** - Every data access includes purpose (why data was accessed)  
✅ **Child Protection Context** - Harmful content detections include child protection context  
✅ **Immutable Audit Trail** - Append-only logging (no deletion/modification)  
✅ **UNICEF Audits** - Logs available for UNICEF compliance audits  
✅ **Child Safety Events** - All child safety events logged  

### **GDPR & COPPA Compliance**

✅ **Data Access Logging** - All data access logged for GDPR compliance  
✅ **Data Subject Rights** - Logs support data subject rights requests  
✅ **COPPA Support** - COPPA flags for children under 13  
✅ **Retention Policies** - Support for GDPR retention requirements  

---

## Audit Log Retention

### **Retention Requirements**

**FERPA:**
- Minimum 7 years

**UNICEF:**
- Minimum 7 years (may require longer depending on project)

**GDPR:**
- Based on legitimate business need
- Typically 3-7 years

**COPPA:**
- 7 years (for children under 13)

### **Retention Policy**

**Recommended:**
- **Active Retention:** 7 years in primary storage
- **Archive:** 7+ years in cold storage (S3 Glacier, etc.)
- **Compliance Access:** Available for audits for full retention period

---

## Access Control

### **Who Can Access Audit Logs**

**Restricted Access:**
- ✅ Compliance officers (read-only)
- ✅ Security team (read-only)
- ✅ System administrators (read-only, limited scope)
- ✅ UNICEF auditors (read-only, specific scope)
- ❌ Regular users (no access)
- ❌ Application code (append-only, no read access)

### **Audit Log Access Control**

**Must Implement:**
- Role-based access control (RBAC)
- Read-only access for compliance team
- Audit trail of audit log access (meta-auditing)
- Encrypted access (TLS/HTTPS)
- Access logging (who accessed audit logs, when, why)

---

## Querying Audit Logs

### **Common Queries**

**1. All data access by a specific user:**
```python
# Query audit logs for user
audit_logs = query_audit_logs(
    event_type="data_access",
    user_id="user_123"
)
```

**2. All harmful content detections:**
```python
# Query harmful content events
harmful_events = query_audit_logs(
    event_type="harmful_content",
    severity=["critical", "high"]
)
```

**3. Data access for a specific student:**
```python
# Query student access history
student_access = query_audit_logs(
    event_type="data_access",
    student_id="student_789"
)
```

**4. UNICEF compliance report:**
```python
# Generate UNICEF compliance report
report = generate_unicef_report(
    school_id="school_456",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

---

## Production Deployment

### **Before Production**

1. **Configure Immutable Storage**
   - Set up S3 bucket with versioning (or equivalent)
   - Configure encryption at rest
   - Set up retention policies
   - Test backup/restore procedures

2. **Set Up Access Controls**
   - Configure RBAC for audit log access
   - Set up compliance team access
   - Configure read-only access
   - Test access controls

3. **Enable Audit Logging**
   - Set `ENABLE_AUDIT_LOGGING=true`
   - Configure production storage
   - Test audit log generation
   - Verify compliance flags

4. **Set Up Monitoring**
   - Monitor audit log generation
   - Alert on audit log failures
   - Monitor storage capacity
   - Set up retention policy alerts

### **In Production**

1. **Monitor Audit Logs**
   - Track audit log volume
   - Monitor storage capacity
   - Alert on audit log failures
   - Regular compliance reviews

2. **Regular Audits**
   - Quarterly compliance reviews
   - UNICEF audit preparation
   - FERPA audit preparation
   - GDPR compliance checks

3. **Maintenance**
   - Regular backups
   - Retention policy enforcement
   - Access control reviews
   - Performance optimization

---

## Security Considerations

### **Privacy**

- **No PII in Logs** - Audit logs don't contain full question text (may contain PII)
- **Question Length Only** - Only question length logged, not full text
- **Text Preview Limited** - Text preview limited to 200 characters (no PII)
- **Redacted Context** - Sensitive context redacted from logs

### **Integrity**

- **Append-Only** - Audit logs are append-only (no deletion/modification)
- **Immutable Storage** - Storage must be immutable (S3 versioning, etc.)
- **Tamper-Proof** - Logs must be tamper-proof (signatures, checksums)
- **Versioning** - Storage must support versioning (S3 versioning, etc.)

### **Availability**

- **High Availability** - Audit log storage must be highly available
- **Backups** - Regular backups of audit logs
- **Disaster Recovery** - Disaster recovery procedures for audit logs
- **Redundancy** - Redundant storage for audit logs

---

## FAQ

### **Q: How long are audit logs retained?**

**A:** 
- Minimum 7 years for FERPA/UNICEF compliance
- May be retained longer based on organizational policy
- Archived logs can be retained indefinitely in cold storage

### **Q: Who can access audit logs?**

**A:**
- Compliance officers (read-only)
- Security team (read-only)
- UNICEF auditors (read-only, specific scope)
- Regular users (no access)

### **Q: Are audit logs encrypted?**

**A:**
- Yes, audit logs are encrypted at rest (if using S3, Cloud Storage, etc.)
- Audit log access is encrypted in transit (TLS/HTTPS)
- Encryption keys are managed securely

### **Q: Can audit logs be deleted or modified?**

**A:**
- No, audit logs are append-only (no deletion/modification)
- Storage must be immutable (S3 versioning, etc.)
- Any deletion/modification would violate compliance requirements

### **Q: How do I generate compliance reports?**

**A:**
- Query audit logs using standard tools (SQL, etc.)
- Generate reports for FERPA/UNICEF audits
- Export logs in required format
- See "Querying Audit Logs" section above

### **Q: What happens if audit logging fails?**

**A:**
- System should fail safely (alert and continue, or fail closed)
- Monitor audit log generation
- Alert on audit log failures
- Retry failed audit log writes

---

## References

- [FERPA Compliance Guide](https://www2.ed.gov/policy/gen/guid/fpco/ferpa/index.html)
- [UNICEF Data Protection Policy](https://www.unicef.org/about/execboard/files/2017-04_DP_Policy-ODS-EN.pdf)
- [GDPR Compliance Guide](https://gdpr.eu/)
- [COPPA Compliance Guide](https://www.ftc.gov/tips-advice/business-center/privacy-and-security/children's-privacy)

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**FERPA & UNICEF Compliance**


