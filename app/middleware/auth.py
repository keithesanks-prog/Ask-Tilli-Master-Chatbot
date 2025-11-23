"""
Authentication Middleware

Provides authentication and authorization for the Master Agent API.
Currently implements basic token-based authentication with JWT support.
"""
import os
import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from functools import wraps

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)

# Configuration (should come from environment variables)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION_USE_COMPLEX_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# For development: allow unauthenticated access if ENABLE_AUTH is not set
REQUIRE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"


class AuthenticationError(HTTPException):
    """Exception raised for authentication errors."""
    pass


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
AUTH0_ALGORITHMS = ["RS256"]

def get_auth0_public_key(token):
    """Fetch JWKS and find the matching key for the token header."""
    try:
        jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
        import requests
        jwks = requests.get(jwks_url).json()
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                return rsa_key
    except Exception as e:
        logger.error(f"Error fetching Auth0 keys: {e}")
        raise HTTPException(status_code=500, detail="Could not verify token signature.")
    return None

def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """
    Verify JWT token from request (supports Auth0 and local dev).
    """
    # If authentication is not required, allow unauthenticated access
    if not REQUIRE_AUTH:
        return {"user_id": "dev_user", "role": "educator", "school_id": "School 1", "authenticated": False}
    
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Mode 1: Auth0 (Production/Staging)
    if AUTH0_DOMAIN and AUTH0_AUDIENCE:
        try:
            rsa_key = get_auth0_public_key(token)
            if rsa_key:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=AUTH0_ALGORITHMS,
                    audience=AUTH0_AUDIENCE,
                    issuer=f"https://{AUTH0_DOMAIN}/"
                )
                # Map Auth0 claims to our user structure
                # Custom claims usually have a namespace, e.g. https://tilli.com/role
                # For now, we'll try standard claims or fallback
                user_id = payload.get("sub")
                
                # Extract role from custom claims or metadata (simplified for now)
                # In a real app, you'd configure a Rule/Action in Auth0 to add this claim
                role = payload.get("https://tilli.com/role", "educator") 
                school_id = payload.get("https://tilli.com/school_id", "School 1") # Default for demo
                
                return {
                    "user_id": user_id,
                    "role": role,
                    "school_id": school_id,
                    "authenticated": True,
                    "provider": "auth0"
                }
            else:
                raise HTTPException(status_code=401, detail="Invalid token signature (key not found)")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token is expired")
        except jwt.JWTClaimsError:
            raise HTTPException(status_code=401, detail="Incorrect claims (check audience/issuer)")
        except Exception as e:
            logger.warning(f"Auth0 validation failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    # Mode 2: Local Dev (HS256)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub") or payload.get("user_id")
        role: str = payload.get("role", "educator")
        school_id: str = payload.get("school_id", "School 1")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        logger.debug(f"Authenticated user: {user_id}, role: {role}")
        return {"user_id": user_id, "role": role, "school_id": school_id, "authenticated": True}
        
    except JWTError as e:
        logger.warning(f"JWT decode error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(allowed_roles: list[str]):
    """
    Dependency factory for role-based access control.
    
    Args:
        allowed_roles: List of allowed roles
        
    Returns:
        Dependency function that checks user role
    """
    def role_checker(current_user: dict = Depends(verify_token)) -> dict:
        if current_user.get("authenticated") and current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_checker


# Convenience dependencies
require_educator = require_role(["educator", "admin"])
require_admin = require_role(["admin"])


