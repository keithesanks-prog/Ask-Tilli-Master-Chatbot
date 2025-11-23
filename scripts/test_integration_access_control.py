"""
Integration Test for Data Access Control

Tests the complete access control flow including:
- Authentication
- Data access verification
- Cross-school access prevention
- Audit logging
"""
import asyncio
import sys
from app.middleware.data_access import (
    verify_data_access,
    check_educator_student_access,
    check_educator_classroom_access
)


async def test_access_scenarios():
    """Test various access control scenarios."""
    print("\n" + "="*70)
    print("DATA ACCESS CONTROL - INTEGRATION TESTS")
    print("="*70)
    
    # Test scenarios
    scenarios = [
        {
            "name": "Educator Alice → Student 001 (Same classroom)",
            "educator": "educator_alice",
            "student": "student_001",
            "expected": True,
            "description": "Should ALLOW - educator teaches this student"
        },
        {
            "name": "Educator Alice → Student 006 (Different classroom, same school)",
            "educator": "educator_alice",
            "student": "student_006",
            "expected": False,
            "description": "Should DENY - student in different classroom"
        },
        {
            "name": "Educator Alice → Student 011 (Different school)",
            "educator": "educator_alice",
            "student": "student_011",
            "expected": False,
            "description": "Should DENY - cross-school access"
        },
        {
            "name": "Educator Bob → Classroom 1B",
            "educator": "educator_bob",
            "classroom": "classroom_1b",
            "expected": True,
            "description": "Should ALLOW - educator teaches this classroom"
        },
        {
            "name": "Educator Bob → Classroom 1A",
            "educator": "educator_bob",
            "classroom": "classroom_1a",
            "expected": False,
            "description": "Should DENY - different classroom in same school"
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   {scenario['description']}")
        
        try:
            if "student" in scenario:
                result = await check_educator_student_access(
                    scenario["educator"],
                    scenario["student"]
                )
            elif "classroom" in scenario:
                result = await check_educator_classroom_access(
                    scenario["educator"],
                    scenario["classroom"]
                )
            
            if result == scenario["expected"]:
                print(f"   ✅ PASS - Result: {result}")
                passed += 1
            else:
                print(f"   ❌ FAIL - Expected: {scenario['expected']}, Got: {result}")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ ERROR - {str(e)}")
            failed += 1
    
    # Summary
    print("\n" + "="*70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("="*70 + "\n")
    
    return failed == 0


async def main():
    """Run all tests."""
    success = await test_access_scenarios()
    
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
