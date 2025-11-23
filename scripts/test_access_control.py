"""
Test Data Access Control

Verify that the database and access control logic works correctly.
"""
import asyncio
from app.services.database import (
    get_educator_classrooms,
    get_student_classrooms,
    get_student_school,
    get_educator_school
)
from app.middleware.data_access import (
    check_educator_student_access,
    check_educator_classroom_access
)


async def test_database():
    """Test database queries."""
    print("\n" + "="*60)
    print("Testing Database Queries")
    print("="*60)
    
    # Test educator classrooms
    print("\n1. Educator Alice's classrooms:")
    classrooms = await get_educator_classrooms("educator_alice")
    print(f"   {classrooms}")
    
    # Test student classrooms
    print("\n2. Student 001's classrooms:")
    classrooms = await get_student_classrooms("student_001")
    print(f"   {classrooms}")
    
    # Test student school
    print("\n3. Student 001's school:")
    school = await get_student_school("student_001")
    print(f"   {school}")
    
    # Test educator school
    print("\n4. Educator Alice's school:")
    school = await get_educator_school("educator_alice")
    print(f"   {school}")


async def test_access_control():
    """Test access control logic."""
    print("\n" + "="*60)
    print("Testing Access Control Logic")
    print("="*60)
    
    # Test 1: Educator Alice should have access to Student 001 (same classroom)
    print("\n1. Can Educator Alice access Student 001? (Expected: True)")
    has_access = await check_educator_student_access("educator_alice", "student_001")
    print(f"   Result: {has_access}")
    
    # Test 2: Educator Alice should NOT have access to Student 006 (different classroom)
    print("\n2. Can Educator Alice access Student 006? (Expected: False)")
    has_access = await check_educator_student_access("educator_alice", "student_006")
    print(f"   Result: {has_access}")
    
    # Test 3: Educator Alice should have access to Classroom 1A
    print("\n3. Can Educator Alice access Classroom 1A? (Expected: True)")
    has_access = await check_educator_classroom_access("educator_alice", "classroom_1a")
    print(f"   Result: {has_access}")
    
    # Test 4: Educator Alice should NOT have access to Classroom 1B
    print("\n4. Can Educator Alice access Classroom 1B? (Expected: False)")
    has_access = await check_educator_classroom_access("educator_alice", "classroom_1b")
    print(f"   Result: {has_access}")
    
    # Test 5: Cross-school access (Educator Alice from School 1, Student 011 from School 2)
    print("\n5. Can Educator Alice access Student 011? (Expected: False - different school)")
    has_access = await check_educator_student_access("educator_alice", "student_011")
    print(f"   Result: {has_access}")


async def main():
    """Run all tests."""
    await test_database()
    await test_access_control()
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
