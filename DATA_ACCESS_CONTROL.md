# Data Access Control - IAM vs Application-Level Authorization

**Understanding the distinction between IAM authentication and data access control**

---

## The Problem

**Current Issue:**
> "Anyone who can authenticate can query any student data"

This is a **data access control** problem, not just an authentication problem.

---

## IAM vs Data Access Control

### **What IAM Provides:**

✅ **Authentication** (Who you are)
- User identity verification
- Login/logout functionality
- Token generation and validation
- Multi-factor authentication (MFA)
- Integration with school identity providers (Google Workspace, Microsoft 365, Clever, etc.)

✅ **Roles** (What role you have)
- Educator role
- Admin role
- Principal role
- District admin role
- Etc.

✅ **Basic Permissions** (What actions you can perform)
- "Can query student data"
- "Can create reports"
- "Can manage users"
- Etc.

### **What IAM DOESN'T Provide:**

❌ **Data Access Control** (Which specific students you can access)
- IAM doesn't know which students are in which educator's classrooms
- IAM doesn't know which schools an educator belongs to
- IAM doesn't know the educator-student-classroom relationships

**This is application-level logic that must be implemented separately.**

---

## How They Work Together

```
┌─────────────────────────────────────────────────────────────┐
│                      IAM (Identity Layer)                    │
│                                                              │
│  1. Authenticates user                                       │
│  2. Returns JWT token with:                                  │
│     - user_id: "educator_123"                                │
│     - role: "educator"                                       │
│     - school_id: "school_456"                                │
│     - email: "teacher@school.edu"                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Application (Authorization Layer)               │
│                                                              │
│  3. Receives request with JWT token                          │
│  4. Extracts user_id, role, school_id from token             │
│  5. Query application database:                              │
│     - Which classrooms does educator_123 teach?              │
│     - Which students are in those classrooms?                │
│     - Does educator_123 have permission for student X?       │
│  6. If YES → Allow access                                    │
│     If NO → Reject with 403 Forbidden                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Approach

### **Step 1: IAM Provides Identity**

**IAM Token Contains:**
```json
{
  "user_id": "educator_123",
  "role": "educator",
  "school_id": "school_456",
  "email": "teacher@school.edu",
  "iat": 1234567890,
  "exp": 1234571490
}
```

### **Step 2: Application Checks Data Access**

**Application Database Contains:**
```sql
-- Educator-Classroom assignments
CREATE TABLE educator_classrooms (
    educator_id VARCHAR(50),
    classroom_id VARCHAR(50),
    school_id VARCHAR(50),
    role VARCHAR(50),  -- 'teacher', 'assistant', etc.
    PRIMARY KEY (educator_id, classroom_id)
);

-- Student-Classroom assignments
CREATE TABLE student_classrooms (
    student_id VARCHAR(50),
    classroom_id VARCHAR(50),
    school_id VARCHAR(50),
    enrollment_date DATE,
    PRIMARY KEY (student_id, classroom_id)
);
```

**Application Logic:**
```python
async def verify_data_access(
    current_user: dict,
    student_id: Optional[str],
    classroom_id: Optional[str],
    grade_level: Optional[str]
) -> bool:
    """
    Check if user has permission to access this data.
    
    This is APPLICATION-LEVEL authorization, not IAM.
    """
    user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    user_school_id = current_user.get("school_id")
    
    # Admins can access all data in their school
    if user_role == "admin":
        return True  # But still check school_id!
    
    # Check school-level access first (multi-tenant isolation)
    if student_id:
        student_school_id = await get_student_school_id(student_id)
        if student_school_id != user_school_id:
            return False  # Cross-tenant access denied
    
    # Check educator-student relationship
    if student_id:
        # Can this educator access this student?
        educator_classrooms = await get_educator_classrooms(user_id)
        student_classrooms = await get_student_classrooms(student_id)
        
        # Check if there's any overlap
        common_classrooms = set(educator_classrooms) & set(student_classrooms)
        if not common_classrooms:
            return False  # Educator doesn't teach this student
    
    # Check classroom-level access
    if classroom_id:
        educator_classrooms = await get_educator_classrooms(user_id)
        if classroom_id not in educator_classrooms:
            return False  # Educator doesn't teach this classroom
    
    return True  # Access granted
```

---

## Where IAM Fits In

### **IAM Handles:**
1. ✅ User authentication (login)
2. ✅ User identity (who they are)
3. ✅ Role assignment (educator, admin)
4. ✅ Token generation/validation
5. ✅ Integration with school identity providers
6. ✅ Multi-factor authentication
7. ✅ Password management
8. ✅ User provisioning/deprovisioning

### **Application Handles:**
1. ✅ Data access control (which students/classrooms)
2. ✅ Educator-classroom assignments
3. ✅ Student-classroom assignments
4. ✅ School-level isolation (multi-tenant)
5. ✅ Row-level security (RLS)
6. ✅ Permission checks per request

---

## Complete Implementation Example

### **1. IAM Integration (OAuth2/OIDC)**

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Verify JWT token from IAM provider (e.g., Google Workspace, Microsoft 365).
    
    This is IAM-level authentication.
    """
    token = credentials.credentials
    
    try:
        # Verify token with IAM provider
        decoded = jwt.decode(
            token,
            IAM_PUBLIC_KEY,  # From IAM provider
            algorithms=["RS256"],
            audience=IAM_AUDIENCE
        )
        
        # Extract user info from token
        return {
            "user_id": decoded["sub"],
            "email": decoded["email"],
            "role": decoded.get("role", "educator"),
            "school_id": decoded.get("school_id"),
            "groups": decoded.get("groups", [])  # From identity provider
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### **2. Data Access Control (Application-Level)**

```python
from fastapi import Depends, HTTPException
from typing import Optional
from app.middleware.auth import verify_token

async def verify_data_access(
    current_user: dict = Depends(verify_token),
    student_id: Optional[str] = None,
    classroom_id: Optional[str] = None
) -> bool:
    """
    Verify that user has permission to access this data.
    
    This is APPLICATION-LEVEL authorization.
    """
    user_id = current_user["user_id"]
    user_role = current_user["role"]
    user_school_id = current_user.get("school_id")
    
    # Admin can access all data in their school
    if user_role == "admin":
        if student_id:
            student_school = await db.get_student_school(student_id)
            if student_school != user_school_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Cross-school access not permitted"
                )
        return True
    
    # For educators, check specific permissions
    if user_role == "educator":
        # Check student access
        if student_id:
            has_access = await check_educator_student_access(
                educator_id=user_id,
                student_id=student_id
            )
            if not has_access:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: You don't have permission to access this student's data"
                )
        
        # Check classroom access
        if classroom_id:
            has_access = await check_educator_classroom_access(
                educator_id=user_id,
                classroom_id=classroom_id
            )
            if not has_access:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: You don't have permission to access this classroom's data"
                )
    
    return True

async def check_educator_student_access(
    educator_id: str,
    student_id: str
) -> bool:
    """
    Check if educator has access to student.
    
    Query application database for educator-student relationship.
    """
    # Get educator's classrooms
    educator_classrooms = await db.query(
        "SELECT classroom_id FROM educator_classrooms WHERE educator_id = %s",
        (educator_id,)
    )
    educator_classroom_ids = [row["classroom_id"] for row in educator_classrooms]
    
    # Get student's classrooms
    student_classrooms = await db.query(
        "SELECT classroom_id FROM student_classrooms WHERE student_id = %s",
        (student_id,)
    )
    student_classroom_ids = [row["classroom_id"] for row in student_classrooms]
    
    # Check if there's overlap
    return bool(set(educator_classroom_ids) & set(student_classroom_ids))

@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: Request,
    ask_request: AskRequest,
    current_user: dict = Depends(verify_token),  # IAM authentication
    _access_verified: bool = Depends(verify_data_access)  # Application authorization
) -> AskResponse:
    """
    Main endpoint with both IAM authentication and data access control.
    """
    # Both checks passed, proceed with request
    ...
```

---

## Recommended Architecture

### **For Tilli (7 Schools, 6,000 Students):**

**1. IAM Layer (Identity Provider Integration)**
- ✅ Integrate with school identity providers (Google Workspace, Microsoft 365)
- ✅ Use OAuth2/OIDC for authentication
- ✅ IAM provides: user_id, email, role, school_id in JWT token

**2. Application Layer (Data Access Control)**
- ✅ Store educator-classroom assignments in application database
- ✅ Store student-classroom assignments in application database
- ✅ Implement `verify_data_access()` function
- ✅ Check permissions on every request
- ✅ Enforce school-level isolation (multi-tenant)

**3. Database Layer (Row-Level Security)**
- ✅ All queries filtered by school_id (multi-tenant isolation)
- ✅ Educator can only query students in their classrooms
- ✅ Implement database-level RLS (if supported)

---

## Summary

**IAM provides:**
- ✅ Authentication (who you are)
- ✅ Roles (educator, admin)
- ✅ Token validation

**Application provides:**
- ✅ Data access control (which students/classrooms)
- ✅ Permission checks per request
- ✅ Row-level security

**They work together:**
1. IAM authenticates user → Returns JWT with user_id, role, school_id
2. Application receives request → Extracts user info from JWT
3. Application checks permissions → Queries database for educator-student relationships
4. If authorized → Allow access
5. If not authorized → Reject with 403 Forbidden

**Both are needed for complete security!**

---

## Next Steps

1. **Integrate IAM** (choose identity provider)
   - See [AUTHENTICATION_OPTIONS.md](AUTHENTICATION_OPTIONS.md)

2. **Implement Data Access Control**
   - Create educator-classroom and student-classroom tables
   - Implement `verify_data_access()` function
   - Add permission checks to all endpoints

3. **Implement Row-Level Security**
   - Filter all queries by school_id
   - Implement database-level RLS (if possible)

4. **Test & Verify**
   - Test cross-tenant access prevention
   - Test educator access to unauthorized students
   - Test admin access scoped to their school

---

**Document Version:** 1.0  
**Last Updated:** 2024

