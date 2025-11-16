"""
FERPA & UNICEF-Compliant Audit Logging Service

Logs all data access, security events, and harmful content detections
for compliance with FERPA, UNICEF, GDPR, and COPPA requirements.

Critical Requirements:
- Must log ALL access to student records (FERPA)
- Must track purpose of access (UNICEF requirement)
- Must maintain immutable audit trail
- Must be tamper-proof and append-only
- 7-year retention minimum (FERPA)
- Available for UNICEF audits
"""
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
import asyncio
import httpx

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    DATA_ACCESS = "data_access"
    HARMFUL_CONTENT = "harmful_content"
    SECURITY_EVENT = "security_event"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    PII_EXPOSURE = "pii_exposure"
    DATA_MISUSE = "data_misuse"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FERPAAuditLogger:
    """
    FERPA and UNICEF-compliant audit logger.
    
    Logs all access to student data, security events, and harmful content detections.
    Aligns with FERPA, UNICEF, GDPR, and COPPA compliance requirements.
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize the audit logger.
        
        Args:
            enabled: Whether to enable audit logging (can be disabled for testing)
        """
        self.enabled = enabled
        self.log_file = os.getenv("AUDIT_LOG_FILE", None)
        self.log_to_file = self.log_file is not None
        self.log_to_stdout = os.getenv("AUDIT_LOG_STDOUT", "true").lower() == "true"
        # Pluggable external sinks (comma-separated): splunk,otlp,syslog,future
        self.enabled_sinks = {
            sink.strip().lower()
            for sink in os.getenv("AUDIT_SINKS", "").split(",")
            if sink.strip()
        }
        # Splunk HEC configuration
        self.splunk_hec_url = os.getenv("SPLUNK_HEC_URL")
        self.splunk_hec_token = os.getenv("SPLUNK_HEC_TOKEN")
        self.splunk_source = os.getenv("SPLUNK_SOURCE", "master-agent")
        self.splunk_sourcetype = os.getenv("SPLUNK_SOURCETYPE", "json")
        self.splunk_index = os.getenv("SPLUNK_INDEX", None)
        # Network timeouts
        self.http_timeout_seconds = float(os.getenv("AUDIT_HTTP_TIMEOUT", "5"))
        self.http_max_retries = int(os.getenv("AUDIT_HTTP_RETRIES", "2"))
        
        if not enabled:
            logger.warning("Audit logging is disabled")
    
    def log_data_access(
        self,
        user_id: str,
        user_email: str,
        user_role: str,
        school_id: str,
        action: str,  # "view", "query", "export"
        purpose: str,  # UNICEF requirement: why data was accessed
        student_id: Optional[str] = None,
        classroom_id: Optional[str] = None,
        grade_level: Optional[str] = None,
        question: Optional[str] = None,
        data_sources_accessed: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log data access for FERPA and UNICEF compliance.
        
        CRITICAL: Must be called for EVERY data access.
        
        Args:
            user_id: User ID accessing data
            user_email: User email address
            user_role: User role (educator, admin, etc.)
            school_id: School ID (tenant)
            action: Action performed ("view", "query", "export")
            purpose: Purpose of access (UNICEF requirement: why data was accessed)
            student_id: Student ID (if applicable)
            classroom_id: Classroom ID (if applicable)
            grade_level: Grade level (if applicable)
            question: User question (length only, not full text - may contain PII)
            data_sources_accessed: List of data sources accessed (REAL, EMT, SEL)
            ip_address: IP address of request
            session_id: Session ID
            metadata: Additional metadata
            
        Returns:
            Audit entry dictionary
        """
        if not self.enabled:
            return {}
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": AuditEventType.DATA_ACCESS.value,
            "severity": AuditSeverity.LOW.value,  # Data access is typically low severity
            "user_id": user_id,
            "user_email": user_email,
            "user_role": user_role,
            "school_id": school_id,
            "action": action,
            "purpose": purpose,  # UNICEF requirement: why data was accessed
            "student_id": student_id,
            "classroom_id": classroom_id,
            "grade_level": grade_level,
            "question_length": len(question) if question else 0,  # Don't log full question (may contain PII)
            "data_sources": data_sources_accessed or [],
            "ip_address": ip_address,
            "session_id": session_id,
            "compliance_flags": {
                "ferpa": True,
                "unicef": True,
                "gdpr": True,  # Will be checked based on school_id if needed
                "coppa": False  # Will be checked based on grade_level if needed
            },
            "metadata": metadata or {}
        }
        
        # Determine COPPA compliance flag
        if grade_level and isinstance(grade_level, str):
            # Extract numeric grade if possible
            try:
                grade_num = int(''.join(filter(str.isdigit, grade_level)))
                if grade_num < 13:
                    audit_entry["compliance_flags"]["coppa"] = True
            except (ValueError, TypeError):
                pass
        
        self._write_audit_log(audit_entry)
        
        return audit_entry
    
    def log_harmful_content(
        self,
        user_id: str,
        user_email: Optional[str],
        school_id: Optional[str],
        severity: str,  # "critical", "high", "medium", "low"
        harm_types: List[str],
        context: str,  # "question" or "response"
        student_id: Optional[str] = None,
        matches_count: int = 0,
        text_preview: Optional[str] = None,  # First 200 chars (no PII)
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        alert_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log harmful content detection for UNICEF child protection compliance.
        
        Args:
            user_id: User ID that triggered detection
            user_email: User email address
            school_id: School ID (tenant)
            severity: Severity level ("critical", "high", "medium", "low")
            harm_types: List of harm types detected
            context: Context of detection ("question" or "response")
            student_id: Student ID (if applicable)
            matches_count: Number of pattern matches
            text_preview: Preview of text (first 200 chars, no PII)
            ip_address: IP address of request
            session_id: Session ID
            alert_metadata: Additional alert metadata
            
        Returns:
            Audit entry dictionary
        """
        if not self.enabled:
            return {}
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": AuditEventType.HARMFUL_CONTENT.value,
            "severity": severity,
            "user_id": user_id,
            "user_email": user_email,
            "school_id": school_id,
            "harm_types": harm_types,
            "context": context,
            "student_id": student_id,
            "matches_count": matches_count,
            "text_preview": text_preview,  # First 200 chars only
            "ip_address": ip_address,
            "session_id": session_id,
            "compliance_flags": {
                "ferpa": True,
                "unicef": True,  # UNICEF child protection compliance
                "gdpr": True,
                "coppa": True  # Child safety concern
            },
            "requires_immediate_action": severity in ["critical", "high"],
            "unicef_aligned": True,
            "metadata": alert_metadata or {}
        }
        
        self._write_audit_log(audit_entry)
        
        # Log to application logger at appropriate level
        if severity == "critical":
            logger.critical(
                f"HARMFUL CONTENT AUDIT (CRITICAL): "
                f"user_id={user_id}, school_id={school_id}, "
                f"types={harm_types}, context={context}"
            )
        elif severity == "high":
            logger.error(
                f"HARMFUL CONTENT AUDIT (HIGH): "
                f"user_id={user_id}, school_id={school_id}, "
                f"types={harm_types}, context={context}"
            )
        else:
            logger.warning(
                f"HARMFUL CONTENT AUDIT ({severity}): "
                f"user_id={user_id}, school_id={school_id}, "
                f"types={harm_types}, context={context}"
            )
        
        return audit_entry
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        school_id: Optional[str] = None,
        description: str = "",
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log general security events.
        
        Args:
            event_type: Type of security event
            severity: Severity level ("critical", "high", "medium", "low")
            user_id: User ID (if applicable)
            user_email: User email (if applicable)
            school_id: School ID (if applicable)
            description: Event description
            ip_address: IP address
            session_id: Session ID
            metadata: Additional metadata
            
        Returns:
            Audit entry dictionary
        """
        if not self.enabled:
            return {}
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": AuditEventType.SECURITY_EVENT.value,
            "severity": severity,
            "user_id": user_id,
            "user_email": user_email,
            "school_id": school_id,
            "security_event_type": event_type,
            "description": description,
            "ip_address": ip_address,
            "session_id": session_id,
            "compliance_flags": {
                "ferpa": True,
                "unicef": True,
                "gdpr": True,
                "coppa": False
            },
            "metadata": metadata or {}
        }
        
        self._write_audit_log(audit_entry)
        
        return audit_entry
    
    def log_pii_exposure(
        self,
        user_id: str,
        user_email: str,
        school_id: str,
        context: str,  # "response", "question", etc.
        entity_types: List[str],  # PII entity types detected
        entities_count: int,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        student_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log PII exposure events for compliance.
        
        Args:
            user_id: User ID
            user_email: User email
            school_id: School ID
            context: Context where PII was detected
            entity_types: Types of PII entities detected
            entities_count: Number of PII entities detected
            ip_address: IP address
            session_id: Session ID
            student_id: Student ID (if applicable)
            
        Returns:
            Audit entry dictionary
        """
        if not self.enabled:
            return {}
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": AuditEventType.PII_EXPOSURE.value,
            "severity": AuditSeverity.HIGH.value,  # PII exposure is high severity
            "user_id": user_id,
            "user_email": user_email,
            "school_id": school_id,
            "context": context,
            "pii_entity_types": entity_types,
            "pii_entities_count": entities_count,
            "student_id": student_id,
            "ip_address": ip_address,
            "session_id": session_id,
            "compliance_flags": {
                "ferpa": True,
                "unicef": True,  # UNICEF zero-tolerance for PII exposure
                "gdpr": True,
                "coppa": True
            },
            "requires_immediate_action": True,  # PII exposure always requires action
            "metadata": {}
        }
        
        self._write_audit_log(audit_entry)
        
        logger.error(
            f"PII EXPOSURE AUDIT: "
            f"user_id={user_id}, school_id={school_id}, "
            f"types={entity_types}, count={entities_count}"
        )
        
        return audit_entry
    
    def _write_audit_log(self, audit_entry: Dict[str, Any]):
        """
        Write audit entry to log storage.
        
        In production, this should write to:
        - Immutable storage (AWS S3, Google Cloud Storage)
        - Audit database (append-only, encrypted)
        - Centralized logging system (ELK, Splunk, etc.)
        
        Args:
            audit_entry: Audit entry dictionary
        """
        # Convert to JSON for logging
        audit_json = json.dumps(audit_entry, ensure_ascii=False, default=str)
        
        # Log to file if configured
        if self.log_to_file and self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(audit_json + "\n")
            except Exception as e:
                logger.error(f"Failed to write audit log to file: {str(e)}")
        
        # Log to stdout (structured logging)
        if self.log_to_stdout:
            logger.info(
                "AUDIT_LOG",
                extra={"audit": audit_entry}
            )
        
        # External sinks
        try:
            if "splunk" in self.enabled_sinks:
                self._forward_to_splunk(audit_entry)
        except Exception as e:
            logger.error(f"Failed to forward audit to external sink: {e}")

    def _forward_to_splunk(self, audit_entry: Dict[str, Any]):
        """
        Forward audit events to Splunk via HTTP Event Collector (HEC).
        Non-blocking with short timeouts and minimal retries to avoid impacting request latency.
        """
        if not (self.splunk_hec_url and self.splunk_hec_token):
            logger.warning("Splunk sink enabled but SPLUNK_HEC_URL or SPLUNK_HEC_TOKEN not set")
            return
        
        # Prepare event payload according to Splunk HEC json format
        payload: Dict[str, Any] = {
            "time": datetime.now(timezone.utc).timestamp(),
            "host": os.getenv("HOSTNAME", "master-agent"),
            "source": self.splunk_source,
            "sourcetype": self.splunk_sourcetype,
            "event": audit_entry,
        }
        if self.splunk_index:
            payload["index"] = self.splunk_index
        
        headers = {
            "Authorization": f"Splunk {self.splunk_hec_token}",
            "Content-Type": "application/json",
        }
        
        async def _send_once():
            async with httpx.AsyncClient(timeout=self.http_timeout_seconds, verify=True) as client:
                resp = await client.post(self.splunk_hec_url, json=payload, headers=headers)
                resp.raise_for_status()
        
        async def _send_with_retries():
            attempts = 0
            last_err = None
            while attempts <= self.http_max_retries:
                try:
                    await _send_once()
                    return
                except Exception as e:
                    last_err = e
                    attempts += 1
            logger.error(f"Splunk HEC forwarding failed after retries: {last_err}")
        
        # Fire-and-forget task; don't block the main request path
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_send_with_retries())
            else:
                loop.run_until_complete(_send_with_retries())
        except RuntimeError:
            # If no loop is available (unlikely in FastAPI), fallback to synchronous send with timeout
            try:
                httpx.post(
                    self.splunk_hec_url,
                    json=payload,
                    headers=headers,
                    timeout=self.http_timeout_seconds
                )
            except Exception as e:
                logger.error(f"Splunk HEC forwarding failed (sync fallback): {e}")


