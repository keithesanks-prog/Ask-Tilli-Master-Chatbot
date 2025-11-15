# Critical Issues Implementation Guide

**Step-by-step guide to address critical security issues before production deployment**

---

## Overview

This guide provides a practical, actionable roadmap to fix the critical security issues identified in the security assessment. The issues are ordered by priority, with the most critical (data access control) addressed first.

---

## 🚨 Priority 1: Data Access Control (CRITICAL BLOCKER)

**Current Issue:** Any authenticated user can access any student's data across all schools.

**Why Critical:**
- 🔴 FERPA violation risk
- 🔴 Data breach: One compromised account = access to all 6,000 students
- 🔴 Multi-tenant isolation failure
- 🔴 Cannot deploy to production without this fix

---

### Implementation Steps

#### **Step 1: Design Data Model**

**Create database schema for educator-student relationships:**

```sql
-- Educators table (if not exists)
CREATE TABLE educators (
    educator_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    school_id VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL,  -- 'educator', 'admin', 'principal', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Educator-Classroom assignments
CREATE TABLE educator_classrooms (
    educator_id VARCHAR(50) NOT NULL,
    classroom_id VARCHAR(50) NOT NULL,
    school_id VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL,  -- 'teacher', 'assistant', 'substitute', etc.
    start_date DATE NOT NULL,
    end_date DATE,  -- NULL if current
    PRIMARY KEY (educator_id, classroom_id),
    FOREIGN KEY (educator_id) REFERENCES educators(educator_id),
    INDEX idx_classroom (classroom_id),
    INDEX idx_school (school_id)
);

-- Student-Classroom assignments
CREATE TABLE student_classrooms (
    student_id VARCHAR(50) NOT NULL,
    classroom_id VARCHAR(50) NOT NULL,
    school_id VARCHAR(50) NOT NULL,
    enrollment_date DATE NOT NULL,
    exit_date DATE,  -- NULL if current
    PRIMARY KEY (student_id, classroom_id),
    INDEX idx_classroom (classroom_id),
    INDEX idx_school (school_id)
);

-- Students table (if not exists)
CREATE TABLE students (
    student_id VARCHAR(50) PRIMARY KEY,
    school_id VARCHAR(50) NOT NULL,
    name VARCHAR(255),  -- Consider PII protection
    grade_level VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_school (school_id),
    INDEX idx_grade (grade_level)
);
```

#### **Step 2: Create Data Access Control Service**

**File: `app/services/data_access_control.py`**

```python
"""
Data Access Control Service

Implements row-level security and permission checks for student data access.
Critical for FERPA compliance and multi-tenant isolation.
"""
import logging
from typing import Optional, List, Set
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class DataAccessControl:
    """
    Manages data access control and permission checks.
    
    Critical Functions:
    - Verify educator can access specific student
    - Verify educator can access specific classroom
    - Enforce school-level isolation (multi-tenant)
    - Row-level security (RLS) checks
    """
    
    def __init__(self, db=None):
        """
        Initialize data access control service.
        
        Args:
            db: Database connection/ORM (e.g., SQLAlchemy session)
        """
        self.db = db
    
    async def verify_student_access(
        self,
        user_id: str,
        user_role: str,
        user_school_id: str,
        student_id: str
    ) -> bool:
        """
        Verify that user has permission to access this student.
        
        Args:
            user_id: Authenticated user ID (from JWT)
            user_role: User role (educator, admin, etc.)
            user_school_id: User's school ID (from JWT)
            student_id: Student ID to check access for
            
        Returns:
            True if access allowed, False otherwise
            
        Raises:
            HTTPException: 403 Forbidden if access denied
        """
        # Admins can access all students in their school
        if user_role == "admin":
            student_school_id = await self._get_student_school_id(student_id)
            if student_school_id != user_school_id:
                logger.warning(
                    f"Admin {user_id} from school {user_school_id} "
                    f"attempted cross-school access to student {student_id}"
                )
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Cross-school access not permitted"
                )
            return True
        
        # For educators, check specific permissions
        if user_role == "educator":
            # Check school-level access first (multi-tenant isolation)
            student_school_id = await self._get_student_school_id(student_id)
            if student_school_id != user_school_id:
                logger.warning(
                    f"Educator {user_id} from school {user_school_id} "
                    f"attempted cross-school access to student {student_id}"
                )
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Cross-school access not permitted"
                )
            
            # Check educator-student relationship
            has_access = await self._check_educator_student_access(
                educator_id=user_id,
                student_id=student_id
            )
            
            if not has_access:
                logger.warning(
                    f"Educator {user_id} attempted unauthorized access "
                    f"to student {student_id}"
                )
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: You don't have permission to access this student's data"
                )
            
            return True
        
        # Unknown role - deny access
        logger.warning(f"Unknown role {user_role} for user {user_id}")
        raise HTTPException(
            status_code=403,
            detail="Access denied: Unknown user role"
        )
    
    async def verify_classroom_access(
        self,
        user_id: str,
        user_role: str,
        user_school_id: str,
        classroom_id: str
    ) -> bool:
        """
        Verify that user has permission to access this classroom.
        
        Args:
            user_id: Authenticated user ID (from JWT)
            user_role: User role (educator, admin, etc.)
            user_school_id: User's school ID (from JWT)
            classroom_id: Classroom ID to check access for
            
        Returns:
            True if access allowed, False otherwise
            
        Raises:
            HTTPException: 403 Forbidden if access denied
        """
        # Admins can access all classrooms in their school
        if user_role == "admin":
            classroom_school_id = await self._get_classroom_school_id(classroom_id)
            if classroom_school_id != user_school_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Cross-school access not permitted"
                )
            return True
        
        # For educators, check specific permissions
        if user_role == "educator":
            # Check school-level access first
            classroom_school_id = await self._get_classroom_school_id(classroom_id)
            if classroom_school_id != user_school_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Cross-school access not permitted"
                )
            
            # Check educator-classroom relationship
            has_access = await self._check_educator_classroom_access(
                educator_id=user_id,
                classroom_id=classroom_id
            )
            
            if not has_access:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: You don't have permission to access this classroom's data"
                )
            
            return True
        
        # Unknown role - deny access
        raise HTTPException(
            status_code=403,
            detail="Access denied: Unknown user role"
        )
    
    async def _check_educator_student_access(
        self,
        educator_id: str,
        student_id: str
    ) -> bool:
        """
        Check if educator has access to student via shared classrooms.
        
        This queries the database to find if educator and student share any classrooms.
        """
        # Get educator's classrooms
        educator_classrooms = await self._get_educator_classrooms(educator_id)
        
        # Get student's classrooms
        student_classrooms = await self._get_student_classrooms(student_id)
        
        # Check if there's overlap
        common_classrooms = set(educator_classrooms) & set(student_classrooms)
        return len(common_classrooms) > 0
    
    async def _check_educator_classroom_access(
        self,
        educator_id: str,
        classroom_id: str
    ) -> bool:
        """Check if educator is assigned to this classroom."""
        educator_classrooms = await self._get_educator_classrooms(educator_id)
        return classroom_id in educator_classrooms
    
    async def _get_educator_classrooms(self, educator_id: str) -> List[str]:
        """Get list of classroom IDs for educator."""
        # TODO: Replace with actual database query
        # Example with SQLAlchemy:
        # result = await self.db.execute(
        #     select(educator_classrooms.c.classroom_id)
        #     .where(educator_classrooms.c.educator_id == educator_id)
        #     .where(educator_classrooms.c.end_date.is_(None))  # Current assignments only
        # )
        # return [row[0] for row in result.fetchall()]
        
        # Placeholder - replace with actual implementation
        return []
    
    async def _get_student_classrooms(self, student_id: str) -> List[str]:
        """Get list of classroom IDs for student."""
        # TODO: Replace with actual database query
        # Example with SQLAlchemy:
        # result = await self.db.execute(
        #     select(student_classrooms.c.classroom_id)
        #     .where(student_classrooms.c.student_id == student_id)
        #     .where(student_classrooms.c.exit_date.is_(None))  # Current enrollments only
        # )
        # return [row[0] for row in result.fetchall()]
        
        # Placeholder - replace with actual implementation
        return []
    
    async def _get_student_school_id(self, student_id: str) -> str:
        """Get school ID for student."""
        # TODO: Replace with actual database query
        # Example:
        # result = await self.db.execute(
        #     select(students.c.school_id)
        #     .where(students.c.student_id == student_id)
        # )
        # row = result.fetchone()
        # return row[0] if row else None
        
        # Placeholder - replace with actual implementation
        return None
    
    async def _get_classroom_school_id(self, classroom_id: str) -> str:
        """Get school ID for classroom."""
        # TODO: Replace with actual database query
        # Example:
        # result = await self.db.execute(
        #     select(educator_classrooms.c.school_id)
        #     .where(educator_classrooms.c.classroom_id == classroom_id)
        #     .limit(1)
        # )
        # row = result.fetchone()
        # return row[0] if row else None
        
        # Placeholder - replace with actual implementation
        return None
```

#### **Step 3: Create Dependency for Data Access Control**

**File: `app/middleware/data_access.py`**

```python
"""
Data Access Control Dependency

FastAPI dependency that verifies data access permissions.
"""
from fastapi import Depends, HTTPException
from typing import Optional
from ..middleware.auth import verify_token
from ..services.data_access_control import DataAccessControl

data_access_control = DataAccessControl()  # Initialize with your DB connection


async def verify_data_access(
    current_user: dict = Depends(verify_token),
    student_id: Optional[str] = None,
    classroom_id: Optional[str] = None,
    grade_level: Optional[str] = None
) -> bool:
    """
    Verify that authenticated user has permission to access requested data.
    
    This dependency should be used on all endpoints that access student data.
    
    Args:
        current_user: Authenticated user info (from verify_token)
        student_id: Optional student ID to check access for
        classroom_id: Optional classroom ID to check access for
        grade_level: Optional grade level filter
        
    Returns:
        True if access allowed
        
    Raises:
        HTTPException: 403 Forbidden if access denied
    """
    user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    user_school_id = current_user.get("school_id")
    
    # Check student access if student_id provided
    if student_id:
        await data_access_control.verify_student_access(
            user_id=user_id,
            user_role=user_role,
            user_school_id=user_school_id,
            student_id=student_id
        )
    
    # Check classroom access if classroom_id provided
    if classroom_id:
        await data_access_control.verify_classroom_access(
            user_id=user_id,
            user_role=user_role,
            user_school_id=user_school_id,
            classroom_id=classroom_id
        )
    
    # TODO: Add grade_level permission checks if needed
    
    return True
```

#### **Step 4: Integrate into Endpoints**

**Update `app/routers/agent.py`:**

```python
from ..middleware.data_access import verify_data_access

@router.post("/ask", response_model=AskResponse)
@limiter.limit(RATE_LIMITS["ask"])
async def ask_question(
    request: Request,
    ask_request: AskRequest,
    current_user: dict = Depends(verify_token),  # IAM authentication
    _access_verified: bool = Depends(  # Application-level authorization
        lambda: verify_data_access(
            current_user=current_user,
            student_id=ask_request.student_id,
            classroom_id=ask_request.classroom_id,
            grade_level=ask_request.grade_level
        )
    )
) -> AskResponse:
    """
    Main endpoint with both IAM authentication and data access control.
    """
    # Both checks passed, proceed with request
    ...
```

**Alternative simpler approach:**

```python
@router.post("/ask", response_model=AskResponse)
@limiter.limit(RATE_LIMITS["ask"])
async def ask_question(
    request: Request,
    ask_request: AskRequest,
    current_user: dict = Depends(verify_token)
) -> AskResponse:
    """Main endpoint with authentication and data access control."""
    
    # Verify data access BEFORE processing request
    data_access = DataAccessControl()
    await data_access.verify_student_access(
        user_id=current_user["user_id"],
        user_role=current_user["role"],
        user_school_id=current_user.get("school_id"),
        student_id=ask_request.student_id or ""  # Handle optional student_id
    )
    
    if ask_request.classroom_id:
        await data_access.verify_classroom_access(
            user_id=current_user["user_id"],
            user_role=current_user["role"],
            user_school_id=current_user.get("school_id"),
            classroom_id=ask_request.classroom_id
        )
    
    # Proceed with request processing...
```

#### **Step 5: Update Database Queries to Enforce RLS**

**All database queries must be filtered by school_id:**

```python
async def fetch_data(
    self,
    data_sources: List[str],
    user_school_id: str,  # Added: From authenticated user
    grade_level: str = None,
    student_id: str = None,
    classroom_id: str = None
) -> AssessmentDataSet:
    """
    Fetch data with row-level security (RLS).
    
    All queries MUST filter by school_id for multi-tenant isolation.
    """
    # Example SQL query with RLS:
    query = """
        SELECT * FROM emt_data
        WHERE school_id = %s  -- CRITICAL: Multi-tenant isolation
        AND student_id = %s
    """
    
    # Always include school_id in queries
    # Never query without school_id filter
```

---

## ✅ Priority 2: Enable Authentication

**Current Issue:** Authentication is implemented but optional by default.

**Fix:**
```bash
export ENABLE_AUTH=true
export JWT_SECRET_KEY="<strong-random-32+-character-secret>"
```

**For Production:**
- Use environment variables or secrets manager
- Generate strong random secret: `openssl rand -hex 32`
- Store in secure location (AWS Secrets Manager, Vault, etc.)

---

## ✅ Priority 3: Add PII Redaction

**Current Issue:** LLM responses may contain student PII.

**Implementation:**

**1. Install Presidio:**
```bash
pip install presidio-analyzer presidio-anonymizer
```

**2. Create PII Redaction Service:**

**File: `app/services/pii_redactor.py`**

```python
"""
PII Redaction Service

Detects and redacts personally identifiable information (PII) from LLM responses.
Critical for FERPA compliance and privacy protection.
"""
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
import logging

logger = logging.getLogger(__name__)


class PIIRedactor:
    """Redacts PII from text responses."""
    
    def __init__(self):
        """Initialize PII redaction engines."""
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
    
    def redact_pii(self, text: str) -> str:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact PII from
            
        Returns:
            Text with PII redacted
        """
        if not text:
            return text
        
        try:
            # Analyze text for PII
            results = self.analyzer.analyze(
                text=text,
                language='en',
                entities=[
                    "PERSON",  # Names
                    "EMAIL_ADDRESS",
                    "PHONE_NUMBER",
                    "CREDIT_CARD",
                    "SSN",  # Social Security Number
                    "US_PASSPORT",
                    "IP_ADDRESS",
                    "DATE_TIME",
                    "LOCATION",
                    "ORGANIZATION"
                ]
            )
            
            # Anonymize detected PII
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results
            )
            
            return anonymized.text
            
        except Exception as e:
            logger.error(f"Error redacting PII: {str(e)}")
            # Fail safe: return original text if redaction fails
            # In production, consider blocking response or alerting
            return text
```

**3. Integrate into LLM Response:**

**Update `app/routers/agent.py`:**

```python
from ..services.pii_redactor import PIIRedactor

pii_redactor = PIIRedactor()

@router.post("/ask", response_model=AskResponse)
async def ask_question(...) -> AskResponse:
    """Main endpoint with PII redaction."""
    
    # Generate LLM response
    response = await llm_engine.generate_response(...)
    
    # Redact PII from response
    sanitized_response = pii_redactor.redact_pii(response)
    
    return AskResponse(
        answer=sanitized_response,
        ...
    )
```

---

## ✅ Priority 4: Configure TLS/HTTPS

**Current Status:** TLS middleware implemented, needs configuration.

**Production Setup:**

**1. Set Environment Variables:**
```bash
export ENVIRONMENT=production
export REQUIRE_TLS=true
export ENFORCE_HTTPS=true
export HSTS_MAX_AGE=31536000
export HSTS_INCLUDE_SUBDOMAINS=true
```

**2. Configure Reverse Proxy (nginx example):**

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.3 TLSv1.2;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;  # CRITICAL: Tells app it's HTTPS
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

**3. Test TLS:**
```bash
curl -I https://your-domain.com/health
# Should return 200 with HSTS headers
```

---

## Implementation Checklist

### Phase 1: Data Access Control (CRITICAL)
- [ ] Design database schema for educator-student relationships
- [ ] Create `DataAccessControl` service
- [ ] Implement `verify_student_access()` function
- [ ] Implement `verify_classroom_access()` function
- [ ] Create database queries for educator-classroom assignments
- [ ] Create database queries for student-classroom assignments
- [ ] Integrate `verify_data_access()` into `/ask` endpoint
- [ ] Add school_id filtering to all database queries (RLS)
- [ ] Test cross-school access prevention
- [ ] Test educator access to unauthorized students
- [ ] Test admin access scoped to their school
- [ ] Update audit logging to include access control checks

### Phase 2: Authentication
- [ ] Set `ENABLE_AUTH=true` in production
- [ ] Generate strong `JWT_SECRET_KEY`
- [ ] Store secrets securely (AWS Secrets Manager/Vault)
- [ ] Integrate with school identity provider (Google Workspace/Microsoft 365)
- [ ] Test authentication flow

### Phase 3: PII Redaction
- [ ] Install Presidio library
- [ ] Create `PIIRedactor` service
- [ ] Integrate into LLM response pipeline
- [ ] Test PII detection and redaction
- [ ] Configure custom entities if needed
- [ ] Add PII exposure alerts

### Phase 4: TLS/HTTPS
- [ ] Set production environment variables
- [ ] Configure reverse proxy (nginx/ALB)
- [ ] Set up SSL certificates (Let's Encrypt/managed)
- [ ] Configure HSTS headers
- [ ] Test HTTPS enforcement
- [ ] Test HTTP to HTTPS redirect

---

## Testing Strategy

### **1. Data Access Control Tests**

```python
def test_cross_school_access_prevention():
    """Test that educators cannot access students from other schools."""
    educator = create_educator(school_id="school_1")
    student = create_student(school_id="school_2")
    
    with pytest.raises(HTTPException) as exc:
        verify_student_access(
            user_id=educator.id,
            user_role="educator",
            user_school_id="school_1",
            student_id=student.id
        )
    
    assert exc.value.status_code == 403

def test_educator_unauthorized_student():
    """Test that educators cannot access students not in their classrooms."""
    educator = create_educator(school_id="school_1")
    classroom = create_classroom(school_id="school_1", educator_id=educator.id)
    student = create_student(school_id="school_1")  # Not in educator's classroom
    
    with pytest.raises(HTTPException) as exc:
        verify_student_access(...)
    
    assert exc.value.status_code == 403

def test_educator_authorized_student():
    """Test that educators CAN access students in their classrooms."""
    educator = create_educator(school_id="school_1")
    classroom = create_classroom(school_id="school_1", educator_id=educator.id)
    student = create_student(school_id="school_1", classroom_id=classroom.id)
    
    result = verify_student_access(...)
    assert result is True
```

### **2. PII Redaction Tests**

```python
def test_pii_redaction():
    """Test that PII is redacted from responses."""
    text = "John Smith scored 85% on the test. Email: john@example.com"
    redacted = pii_redactor.redact_pii(text)
    
    assert "John Smith" not in redacted
    assert "john@example.com" not in redacted
    assert "<PERSON>" in redacted or "<EMAIL_ADDRESS>" in redacted
```

---

## Timeline Recommendation

**Week 1-2: Data Access Control (CRITICAL)**
- Design schema
- Implement `DataAccessControl` service
- Integrate into endpoints
- Test thoroughly

**Week 2-3: Authentication**
- Enable authentication
- Integrate with identity provider
- Test authentication flow

**Week 3-4: PII Redaction**
- Install Presidio
- Implement redaction service
- Integrate into response pipeline
- Test PII detection

**Week 4: TLS/HTTPS**
- Configure reverse proxy
- Set up SSL certificates
- Test HTTPS enforcement

---

## Next Steps

1. **Review this guide** with your team
2. **Prioritize data access control** - Start immediately
3. **Set up database schema** - Create educator-student relationship tables
4. **Implement `DataAccessControl` service** - Start with basic version
5. **Test thoroughly** - Especially cross-school access prevention
6. **Iterate** - Add features incrementally

---

## Resources

- [DATA_ACCESS_CONTROL.md](DATA_ACCESS_CONTROL.md) - Detailed IAM vs Application-level authorization guide
- [AUTHENTICATION_OPTIONS.md](AUTHENTICATION_OPTIONS.md) - IAM/identity provider options
- [TLS_CONFIGURATION.md](TLS_CONFIGURATION.md) - TLS/HTTPS setup guide
- [SECURITY_ASSESSMENT.md](SECURITY_ASSESSMENT.md) - Complete security assessment

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**Priority:** 🚨 CRITICAL - Start with Data Access Control immediately

