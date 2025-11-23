"""
Database Service

Handles database connections and queries for data access control.
Uses SQLite for development/testing.
"""
import sqlite3
import os
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Database file path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "access_control.db")


@contextmanager
def get_db_connection():
    """Get database connection with automatic cleanup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize database schema."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Educator-Classroom assignments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS educator_classrooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                educator_id TEXT NOT NULL,
                classroom_id TEXT NOT NULL,
                school_id TEXT NOT NULL,
                role TEXT DEFAULT 'teacher',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(educator_id, classroom_id)
            )
        """)
        
        # Student-Classroom assignments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_classrooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                classroom_id TEXT NOT NULL,
                school_id TEXT NOT NULL,
                enrollment_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, classroom_id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_educator_classrooms_educator 
            ON educator_classrooms(educator_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_educator_classrooms_school 
            ON educator_classrooms(school_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_classrooms_student 
            ON student_classrooms(student_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_classrooms_classroom 
            ON student_classrooms(classroom_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_classrooms_school 
            ON student_classrooms(school_id)
        """)
        
        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")


async def get_educator_classrooms(educator_id: str) -> List[str]:
    """
    Get all classroom IDs for an educator.
    
    Args:
        educator_id: Educator's user ID
        
    Returns:
        List of classroom IDs
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT classroom_id FROM educator_classrooms WHERE educator_id = ?",
            (educator_id,)
        )
        return [row["classroom_id"] for row in cursor.fetchall()]


async def get_student_classrooms(student_id: str) -> List[str]:
    """
    Get all classroom IDs for a student.
    
    Args:
        student_id: Student's ID
        
    Returns:
        List of classroom IDs
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT classroom_id FROM student_classrooms WHERE student_id = ?",
            (student_id,)
        )
        return [row["classroom_id"] for row in cursor.fetchall()]


async def get_student_school(student_id: str) -> Optional[str]:
    """
    Get the school ID for a student.
    
    Args:
        student_id: Student's ID
        
    Returns:
        School ID or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT school_id FROM student_classrooms WHERE student_id = ? LIMIT 1",
            (student_id,)
        )
        row = cursor.fetchone()
        return row["school_id"] if row else None


async def get_educator_school(educator_id: str) -> Optional[str]:
    """
    Get the school ID for an educator.
    
    Args:
        educator_id: Educator's user ID
        
    Returns:
        School ID or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT school_id FROM educator_classrooms WHERE educator_id = ? LIMIT 1",
            (educator_id,)
        )
        row = cursor.fetchone()
        return row["school_id"] if row else None


def add_educator_classroom(educator_id: str, classroom_id: str, school_id: str, role: str = "teacher"):
    """Add educator-classroom assignment."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO educator_classrooms (educator_id, classroom_id, school_id, role)
            VALUES (?, ?, ?, ?)
            """,
            (educator_id, classroom_id, school_id, role)
        )
        conn.commit()


def add_student_classroom(student_id: str, classroom_id: str, school_id: str):
    """Add student-classroom assignment."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO student_classrooms (student_id, classroom_id, school_id)
            VALUES (?, ?, ?)
            """,
            (student_id, classroom_id, school_id)
        )
        conn.commit()


# Initialize database on module import
init_database()
