"""
Data Access Control Middleware

Verifies that users have permission to access requested data.
Implements application-level authorization (not IAM authentication).
"""
import os
import logging
from typing import Optional
from fastapi import HTTPException, Depends

from ..middleware.auth import verify_token
from ..services.database import (
    get_educator_classrooms,
    get_student_classrooms,
    get_student_school,
    get_educator_school
)

logger = logging.getLogger(__name__)

# Feature flag - can be disabled for testing
ENABLE_DATA_ACCESS_CONTROL = os.getenv("ENABLE_DATA_ACCESS_CONTROL", "false").lower() == "true"


async def verify_data_access(
    current_user: dict = Depends(verify_token),
    student_id: Optional[str] = None,
    classroom_id: Optional[str] = None,
    grade_level: Optional[str] = None
) -> bool:
    """
    Verify that user has permission to access the requested data.
    
    This implements APPLICATION-LEVEL authorization (not IAM).
    
    Args:
        current_user: User info from JWT token (from verify_token)
        student_id: Optional student ID filter
        classroom_id: Optional classroom ID filter
        grade_level: Optional grade level filter
        
    Returns:
        True if access is granted
        
    Raises:
        HTTPException: 403 Forbidden if access is denied
    """
    # If data access control is disabled, allow all requests
    if not ENABLE_DATA_ACCESS_CONTROL:
        logger.debug("Data access control is disabled - allowing request")
        return True
    
    user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    user_school_id = current_user.get("school_id")
    
    logger.info(
        f"Checking data access: user={user_id}, role={user_role}, "
        f"student_id={student_id}, classroom_id={classroom_id}"
    )
    
    # Admins can access all data in their school
    if user_role == "admin":
        # Still enforce school-level isolation
        if student_id:
            student_school = await get_student_school(student_id)
            if student_school and student_school != user_school_id:
                logger.warning(
                    f"Admin {user_id} attempted cross-school access: "
                    f"user_school={user_school_id}, student_school={student_school}"
                )
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Cross-school access not permitted"
                )
        logger.info(f"Admin {user_id} granted access")
        return True
    
    # For educators, check specific permissions
    if user_role == "educator":
        # Check student access
        if student_id:
            has_access = await check_educator_student_access(user_id, student_id)
            if not has_access:
                logger.warning(
                    f"Educator {user_id} denied access to student {student_id}"
                )
                # Generic error - no data leakage
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: You are not authorized to view this student or class."
                )
        
        # Check classroom access
        if classroom_id:
            has_access = await check_educator_classroom_access(user_id, classroom_id)
            if not has_access:
                logger.warning(
                    f"Educator {user_id} denied access to classroom {classroom_id}"
                )
                # Generic error - no data leakage
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: You are not authorized to view this student or class."
                )
        
        logger.info(f"Educator {user_id} granted access")
        return True
    
    # Unknown role - deny by default
    logger.warning(f"Unknown role {user_role} for user {user_id} - denying access")
    # Generic error - no data leakage
    raise HTTPException(
        status_code=403,
        detail="Access denied: You are not authorized to view this student or class."
    )


async def check_educator_student_access(educator_id: str, student_id: str) -> bool:
    """
    Check if educator has access to a specific student.
    
    Args:
        educator_id: Educator's user ID
        student_id: Student's ID
        
    Returns:
        True if educator teaches this student
    """
    # Get educator's classrooms
    educator_classrooms = await get_educator_classrooms(educator_id)
    
    # Get student's classrooms
    student_classrooms = await get_student_classrooms(student_id)
    
    # Check if there's any overlap
    common_classrooms = set(educator_classrooms) & set(student_classrooms)
    
    logger.debug(
        f"Educator {educator_id} classrooms: {educator_classrooms}, "
        f"Student {student_id} classrooms: {student_classrooms}, "
        f"Common: {common_classrooms}"
    )
    
    return bool(common_classrooms)


async def check_educator_classroom_access(educator_id: str, classroom_id: str) -> bool:
    """
    Check if educator has access to a specific classroom.
    
    Args:
        educator_id: Educator's user ID
        classroom_id: Classroom ID
        
    Returns:
        True if educator teaches this classroom
    """
    educator_classrooms = await get_educator_classrooms(educator_id)
    
    logger.debug(
        f"Educator {educator_id} classrooms: {educator_classrooms}, "
        f"Checking access to: {classroom_id}"
    )
    
    return classroom_id in educator_classrooms
