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


def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """
    Verify JWT token from request.
    
    Args:
        credentials: HTTP bearer credentials from request
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or missing (when auth is required)
    """
    # If authentication is not required, allow unauthenticated access
    if not REQUIRE_AUTH:
        return {"user_id": "dev_user", "role": "educator", "authenticated": False}
    
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub") or payload.get("user_id")
        role: str = payload.get("role", "educator")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        logger.debug(f"Authenticated user: {user_id}, role: {role}")
        return {"user_id": user_id, "role": role, "authenticated": True}
        
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


