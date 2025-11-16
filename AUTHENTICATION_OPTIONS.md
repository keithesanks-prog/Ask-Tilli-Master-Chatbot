# Authentication & Authorization Options

This document explains the authentication and authorization options for the Master Agent, including whether you need IAM and what alternatives exist.

## Current Implementation

**What We Have Now:**
- ✅ Basic JWT-based authentication
- ✅ Role-based access control (RBAC) framework
- ✅ Token verification
- ❌ No user management
- ❌ No identity provider integration
- ❌ No data access control

**Current Limitations:**
- JWT tokens are self-signed (no external identity verification)
- No user database/management
- No integration with school/district identity systems
- No fine-grained permissions (can't check which students/classrooms user can access)

---

## Do You Need IAM?

### **Short Answer:**
- **For simple use case**: Basic JWT + user database might be enough
- **For production/enterprise**: Yes, you'll likely need IAM or an identity provider
- **For educational platforms**: Usually need integration with school identity providers

### **What IAM Provides:**
1. **User Management** (CRUD operations)
2. **Identity Provider Integration** (Google Workspace, Microsoft 365, Clever, etc.)
3. **Role & Permission Management**
4. **Session Management**
5. **Multi-Factor Authentication (MFA)**
6. **Password Policies**
7. **Audit Logging**
8. **Fine-grained Access Control**

---

## Options by Complexity & Use Case

### **Option 1: Simple JWT + User Database** (Current)

**Best For:** Small deployments, prototypes, development

**What It Provides:**
- ✅ JWT token generation and verification
- ✅ Role-based access (educator, admin)
- ✅ Basic authentication

**What It Doesn't Provide:**
- ❌ User registration/login endpoints
- ❌ Password management
- ❌ Identity provider integration
- ❌ Fine-grained permissions
- ❌ Data access control (can't check student permissions)

**Current Code:**
```python
# What we have:
- JWT token creation/verification
- Role checking (educator/admin)
- Basic user info in token
```

**To Use:**
```bash
export ENABLE_AUTH=true
export JWT_SECRET_KEY="your-secret"
```

**Limitations:**
- Must build your own user management
- Must build your own login/registration
- No integration with school systems
- Can't verify which students educator should access

---

### **Option 2: Integrated IAM Service**

**Best For:** Production deployments, enterprise, multi-tenant

**Options:**

#### **A. AWS Cognito** (Recommended for AWS deployments)

**Pros:**
- ✅ Managed service (no infrastructure to manage)
- ✅ User management built-in
- ✅ Supports federated identity (Google, Microsoft, SAML)
- ✅ MFA support
- ✅ Scales automatically
- ✅ Works with school identity providers

**Cons:**
- ⚠️ AWS-specific (vendor lock-in)
- ⚠️ Costs money (but reasonable)
- ⚠️ Learning curve

**Integration:**
```python
# Use boto3 to verify Cognito tokens
from boto3 import client as boto3_client
cognito = boto3_client('cognito-idp')

def verify_cognito_token(token: str) -> dict:
    # Verify token with Cognito
    # Get user info and permissions
    pass
```

**Cost:** ~$0.0055 per MAU (Monthly Active User), first 50k MAU free

#### **B. Auth0** (Recommended for flexibility)

**Pros:**
- ✅ Multi-cloud (not vendor-locked)
- ✅ Excellent documentation
- ✅ Supports many identity providers
- ✅ Built-in social login
- ✅ Good for educational platforms

**Cons:**
- ⚠️ Costs money
- ⚠️ External dependency

**Integration:**
```python
# Verify Auth0 JWT
from jose import jwt, jwk
import requests

def verify_auth0_token(token: str) -> dict:
    # Verify with Auth0's JWKS
    # Get user info and permissions
    pass
```

**Cost:** Free tier for 7,000 MAU, then paid plans

#### **C. Firebase Authentication** (Google ecosystem)

**Pros:**
- ✅ Free tier is generous
- ✅ Easy Google Workspace integration
- ✅ Simple integration

**Cons:**
- ⚠️ Google-specific
- ⚠️ Limited customization

**Good For:** If already using Google Cloud/Workspace

---

### **Option 3: Self-Hosted IAM Solutions**

#### **A. Keycloak** (Open Source)

**Pros:**
- ✅ Free and open source
- ✅ Full-featured IAM
- ✅ Supports OAuth2, OIDC, SAML
- ✅ Self-hosted (full control)
- ✅ Can integrate with school identity providers

**Cons:**
- ⚠️ Requires infrastructure to run
- ⚠️ More setup/maintenance

**Best For:** Organizations wanting full control, avoiding vendor lock-in

#### **B. Ory Kratos/Hydra** (Open Source)

**Pros:**
- ✅ Modern, cloud-native
- ✅ Microservices-friendly
- ✅ OAuth2/OIDC support

**Cons:**
- ⚠️ More complex setup
- ⚠️ Requires more technical expertise

---

### **Option 4: Educational-Specific Identity Providers**

For educational platforms like Tilli, you likely want to integrate with:

#### **A. Google Workspace for Education** ⭐ **RECOMMENDED**

**Why:**
- Most schools use Google Workspace
- Educators already have accounts
- Single Sign-On (SSO)
- Free for schools

**Integration:**
```python
# Use Google OAuth2/OIDC
from google.auth.transport import requests
from google.oauth2 import id_token

def verify_google_token(token: str) -> dict:
    # Verify with Google
    idinfo = id_token.verify_oauth2_token(
        token, requests.Request(), GOOGLE_CLIENT_ID
    )
    return {
        "user_id": idinfo['sub'],
        "email": idinfo['email'],
        "name": idinfo['name'],
        "domain": idinfo.get('hd'),  # School domain
        "role": determine_role_from_domain(idinfo)
    }
```

#### **B. Microsoft Azure AD (Microsoft 365 Education)**

**Why:**
- Many schools use Microsoft 365
- Good enterprise features
- SSO support

**Integration:**
```python
# Use Microsoft Graph API / OAuth2
# Verify tokens with Microsoft's JWKS
```

#### **C. Clever** (Popular in US schools)

**Why:**
- Widely used in US K-12
- Handles identity for multiple districts
- Easy integration for education apps

**Integration:**
```python
# Use Clever OAuth API
# Clever provides district/user info
```

#### **D. ClassLink** (Popular in education)

**Why:**
- Common in US schools
- Provides identity and roster data
- Good for education apps

---

## Recommended Architecture for Tilli

### **Recommended: OAuth2/OIDC with School Identity Provider**

```
Educator → Frontend → School Identity Provider (Google Workspace/Microsoft 365)
                                      ↓
                               OAuth2/OIDC Token
                                      ↓
                              Master Agent API
                                      ↓
                         Verify Token with Identity Provider
                                      ↓
                         Check User Permissions in Tilli DB
                                      ↓
                         Allow/Deny Access to Student Data
```

### **Why This Approach:**

1. **Educators already have accounts** - No new passwords
2. **FERPA Compliance** - School manages identity
3. **SSO Experience** - Better UX
4. **District-Managed** - Schools control access

---

## Implementation Strategy

### **Phase 1: Basic IAM** (Current → Next Step)

**What to Add:**
1. User database/model
2. Login/registration endpoints
3. Password hashing
4. Token generation tied to users
5. Basic data access control

**Files to Create:**
- `app/models/user_models.py` - User, Role models
- `app/services/user_service.py` - User management
- `app/routers/auth.py` - Login, register endpoints
- Database schema for users, roles, permissions

**This Gets You:**
- User management
- Basic authentication
- Still simple, no external dependencies

---

### **Phase 2: Identity Provider Integration** (Production)

**What to Add:**
1. OAuth2/OIDC integration
2. Support for Google Workspace / Microsoft 365
3. Token verification with identity provider
4. User mapping (school account → Tilli user)

**Dependencies:**
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2
# or
pip install msal  # For Microsoft
```

**This Gets You:**
- SSO with school accounts
- No password management
- FERPA-compliant identity
- Better UX for educators

---

### **Phase 3: Full IAM** (Enterprise)

**What to Add:**
1. IAM service (Cognito, Auth0, or Keycloak)
2. Fine-grained permissions
3. Multi-factor authentication
4. Advanced audit logging

**This Gets You:**
- Enterprise-grade security
- MFA support
- Advanced features
- May be overkill for smaller deployments

---

## Data Access Control (Critical Missing Piece)

Regardless of which IAM option you choose, you need:

### **Permission Model:**

```python
# User Model
class User(BaseModel):
    user_id: str
    email: str
    role: str  # educator, admin, etc.
    
# Permission Model
class UserPermission(BaseModel):
    user_id: str
    classroom_ids: List[str]  # Which classrooms can user access?
    student_ids: List[str]     # Which students can user access?
    grade_levels: List[str]    # Which grade levels?
    school_id: Optional[str]   # Which school?
    district_id: Optional[str] # Which district?

# Service to check permissions
async def verify_data_access(
    user_id: str,
    student_id: Optional[str],
    classroom_id: Optional[str],
    grade_level: Optional[str]
) -> bool:
    """
    Check if user has permission to access requested data.
    This is CRITICAL for FERPA compliance.
    """
    user_perms = get_user_permissions(user_id)
    
    # Check classroom access
    if classroom_id and classroom_id not in user_perms.classroom_ids:
        return False
    
    # Check student access
    if student_id and student_id not in user_perms.student_ids:
        return False
    
    # Check grade level
    if grade_level and grade_level not in user_perms.grade_levels:
        return False
    
    return True
```

---

## Comparison Table

| Feature | Simple JWT | OAuth2/OIDC | Cognito | Auth0 | Keycloak |
|---------|-----------|-------------|---------|-------|----------|
| **User Management** | ❌ Build yourself | ⚠️ Identity Provider | ✅ Built-in | ✅ Built-in | ✅ Built-in |
| **School Integration** | ❌ No | ✅ Yes (Google/Microsoft) | ✅ Yes | ✅ Yes | ✅ Yes |
| **Cost** | Free | Free | $0.0055/MAU | Free tier → Paid | Free |
| **Setup Complexity** | Low | Medium | Low | Low | High |
| **Maintenance** | High | Low | None | None | High |
| **MFA Support** | ❌ Build yourself | ⚠️ Depends on provider | ✅ Yes | ✅ Yes | ✅ Yes |
| **Fine-grained Permissions** | ❌ Build yourself | ⚠️ Depends on provider | ✅ Yes | ✅ Yes | ✅ Yes |
| **FERPA Compliance** | ⚠️ With custom code | ✅ With school provider | ✅ Yes | ✅ Yes | ✅ Yes |

---

## Recommended Path for Tilli

### **Development/Testing:**
✅ **Current approach (Simple JWT)** is fine
- Fast to implement
- Good for testing
- No external dependencies

### **Production (MVP):**
✅ **Add OAuth2/OIDC with Google Workspace**
- Most schools use Google
- Educators already have accounts
- FERPA-compliant
- Better UX (SSO)

**Implementation:**
```python
# app/middleware/auth.py - Enhanced
def verify_google_token(token: str) -> dict:
    """Verify token from Google Workspace."""
    # Verify with Google
    # Get user info
    # Map to Tilli user/permissions
    pass
```

### **Enterprise/Scale:**
✅ **Add IAM Service (Cognito or Auth0)**
- When you need advanced features
- When you need multiple identity providers
- When you need MFA
- When user base grows

---

## Code Example: Google Workspace Integration

```python
# app/middleware/auth_google.py
from google.auth.transport import requests
from google.oauth2 import id_token
from typing import Optional

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def verify_google_workspace_token(token: str) -> dict:
    """
    Verify Google Workspace OAuth2 token.
    
    Returns:
        User info including email, domain, role
    """
    try:
        # Verify token with Google
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # Check if it's from a Google Workspace domain
        domain = idinfo.get('hd')  # Hosted domain
        if not domain:
            raise HTTPException(401, "Not a Google Workspace account")
        
        # Map to Tilli user
        user_info = {
            "user_id": idinfo['sub'],
            "email": idinfo['email'],
            "name": idinfo.get('name'),
            "domain": domain,
            "picture": idinfo.get('picture'),
        }
        
        # Determine role from domain/permissions
        # (e.g., check against Tilli's user database)
        user_permissions = get_tilli_user_permissions(user_info['email'])
        
        return {
            **user_info,
            "role": user_permissions.get('role', 'educator'),
            "classroom_ids": user_permissions.get('classroom_ids', []),
            "school_id": user_permissions.get('school_id'),
            "authenticated": True
        }
        
    except ValueError:
        raise HTTPException(401, "Invalid Google token")
```

---

## Dependencies Needed

### **For Google Workspace Integration:**
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2
```

### **For Microsoft 365 Integration:**
```bash
pip install msal
```

### **For Generic OAuth2/OIDC:**
```bash
pip install authlib  # Good OAuth2/OIDC library
```

---

## Summary

### **Do You Need IAM?**

**Simple Answer:**
- **For development**: No, current JWT is fine
- **For production**: Yes, but start with OAuth2/OIDC integration (simpler than full IAM)
- **For enterprise**: Yes, consider managed IAM service

**Recommended for Tilli:**
1. **Start**: Current JWT + user database + data access control
2. **Production**: Add Google Workspace OAuth2/OIDC integration
3. **Scale**: Add IAM service (Cognito/Auth0) if needed

**Key Point:** The most critical missing piece is **data access control** (checking which students/classrooms a user can access). This is needed regardless of IAM solution.

See implementation examples above for Google Workspace integration.


