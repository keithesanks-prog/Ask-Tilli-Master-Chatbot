"""
Sample Data Generator for Access Control

Creates sample educator-classroom and student-classroom assignments for testing.
"""
from app.services.database import add_educator_classroom, add_student_classroom
import logging

logger = logging.getLogger(__name__)


def create_sample_data():
    """
    Create sample data for testing data access control.
    
    Sample structure:
    - School 1:
        - Classroom 1A: Educator Alice, Students 1-5
        - Classroom 1B: Educator Bob, Students 6-10
    - School 2:
        - Classroom 2A: Educator Carol, Students 11-15
        - Classroom 2B: Educator Dave, Students 16-20
    """
    
    # School 1 - Classroom 1A
    add_educator_classroom("educator_alice", "classroom_1a", "school_1", "teacher")
    for i in range(1, 6):
        add_student_classroom(f"student_{i:03d}", "classroom_1a", "school_1")
    
    # School 1 - Classroom 1B
    add_educator_classroom("educator_bob", "classroom_1b", "school_1", "teacher")
    for i in range(6, 11):
        add_student_classroom(f"student_{i:03d}", "classroom_1b", "school_1")
    
    # School 2 - Classroom 2A
    add_educator_classroom("educator_carol", "classroom_2a", "school_2", "teacher")
    for i in range(11, 16):
        add_student_classroom(f"student_{i:03d}", "classroom_2a", "school_2")
    
    # School 2 - Classroom 2B
    add_educator_classroom("educator_dave", "classroom_2b", "school_2", "teacher")
    for i in range(16, 21):
        add_student_classroom(f"student_{i:03d}", "classroom_2b", "school_2")
    
    logger.info("Sample data created successfully")
    print("✓ Sample data created:")
    print("  - School 1: 2 classrooms, 2 educators, 10 students")
    print("  - School 2: 2 classrooms, 2 educators, 10 students")


if __name__ == "__main__":
    create_sample_data()
