"""
Test script for the authentication system.
Verifies CSV parsing and database operations.
"""
import asyncio
from sqlalchemy import select

from db import AsyncSessionLocal, init_db
from db.models import AuthenticatedUser, Professional, ProfessionalCourseChannel, PendingAuth
from utils.csv_parser import find_student_by_id, get_all_students


async def test_csv_parser():
    """Test CSV parsing functionality."""
    print("\n" + "="*50)
    print("Testing CSV Parser")
    print("="*50)
    
    # Test finding a student
    print("\n1. Testing find_student_by_id()...")
    student = find_student_by_id("22108121", "M1")
    if student:
        print(f"   ✓ Found student: {student['first_name']} {student['last_name']}")
        print(f"     Email: {student['email']}")
        print(f"     Formation: {student['formation_type']}")
        print(f"     Grade: {student['grade_level']}")
    else:
        print("   ✗ Student not found")
    
    # Test getting all students
    print("\n2. Testing get_all_students()...")
    all_students = get_all_students()
    print(f"   ✓ Found {len(all_students)} students total")
    
    m1_students = get_all_students("M1")
    print(f"   ✓ Found {len(m1_students)} M1 students")
    
    m2_students = get_all_students("M2")
    print(f"   ✓ Found {len(m2_students)} M2 students")
    
    # Count by formation
    fi_count = len([s for s in all_students if s['formation_type'] == 'FI'])
    fa_count = len([s for s in all_students if s['formation_type'] == 'FA'])
    print(f"   ✓ FI: {fi_count}, FA: {fa_count}")


async def test_database_operations():
    """Test database operations."""
    print("\n" + "="*50)
    print("Testing Database Operations")
    print("="*50)
    
    # Initialize database
    await init_db()
    print("\n✓ Database initialized")
    
    async with AsyncSessionLocal() as session:
        # Test Professional creation
        print("\n1. Testing Professional creation...")
        
        # Check if test professional exists
        result = await session.execute(
            select(Professional).where(Professional.email == "test@u-paris.fr")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("   ⚠ Test professional already exists, cleaning up...")
            await session.delete(existing)
            await session.commit()
        
        # Create test professional
        pro = Professional(
            email="test@u-paris.fr",
            first_name="Test",
            last_name="Professional"
        )
        session.add(pro)
        await session.commit()
        print(f"   ✓ Created professional: {pro.email} (ID: {pro.id})")
        
        # Test ProfessionalCourseChannel creation
        print("\n2. Testing course channel assignment...")
        course_channel = ProfessionalCourseChannel(
            professional_id=pro.id,
            channel_id=123456789,
            channel_name="Test Course"
        )
        session.add(course_channel)
        await session.commit()
        print(f"   ✓ Assigned course channel: {course_channel.channel_name}")
        
        # Test AuthenticatedUser (student)
        print("\n3. Testing AuthenticatedUser (student) creation...")
        
        # Clean up if exists
        result = await session.execute(
            select(AuthenticatedUser).where(AuthenticatedUser.user_id == 999999)
        )
        existing = result.scalar_one_or_none()
        if existing:
            await session.delete(existing)
            await session.commit()
        
        student_user = AuthenticatedUser(
            user_id=999999,
            email="test.student@etu.u-paris.fr",
            user_type='student',
            student_id="12345678",
            grade_level="M1",
            formation_type="FI",
            rootme_id="123456",
            linkedin_url="https://linkedin.com/in/test"
        )
        session.add(student_user)
        await session.commit()
        print(f"   ✓ Created student user: {student_user.email}")
        
        # Test AuthenticatedUser (professional)
        print("\n4. Testing AuthenticatedUser (professional) creation...")
        
        # Clean up if exists
        result = await session.execute(
            select(AuthenticatedUser).where(AuthenticatedUser.user_id == 888888)
        )
        existing = result.scalar_one_or_none()
        if existing:
            await session.delete(existing)
            await session.commit()
        
        pro_user = AuthenticatedUser(
            user_id=888888,
            email="test@u-paris.fr",
            user_type='professional'
        )
        session.add(pro_user)
        await session.commit()
        print(f"   ✓ Created professional user: {pro_user.email}")
        
        # Test PendingAuth
        print("\n5. Testing PendingAuth creation...")
        
        # Clean up if exists
        result = await session.execute(
            select(PendingAuth).where(PendingAuth.user_id == 777777)
        )
        existing = result.scalar_one_or_none()
        if existing:
            await session.delete(existing)
            await session.commit()
        
        from datetime import datetime, timedelta
        pending = PendingAuth(
            user_id=777777,
            email="pending@etu.u-paris.fr",
            token="test_token_123",
            user_type='student',
            student_id="87654321",
            grade_level="M2",
            formation_type="FA",
            first_name="Test",
            last_name="Pending",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        session.add(pending)
        await session.commit()
        print(f"   ✓ Created pending auth: {pending.email}")
        
        # Verify relationships
        print("\n6. Testing relationships...")
        from sqlalchemy.orm import selectinload
        result = await session.execute(
            select(Professional).where(Professional.id == pro.id).options(selectinload(Professional.course_channels))
        )
        pro_with_courses = result.scalar_one_or_none()
        print(f"   ✓ Professional has {len(pro_with_courses.course_channels)} course(s)")
        
        # Clean up test data
        print("\n7. Cleaning up test data...")
        await session.delete(pending)
        await session.delete(pro_user)
        await session.delete(student_user)
        await session.delete(course_channel)
        await session.delete(pro)
        await session.commit()
        print("   ✓ Test data cleaned up")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print(" AUTHENTICATION SYSTEM TEST SUITE")
    print("="*60)
    
    try:
        await test_csv_parser()
        await test_database_operations()
        
        print("\n" + "="*60)
        print(" ALL TESTS PASSED ✓")
        print("="*60 + "\n")
        
    except Exception as e:
        print("\n" + "="*60)
        print(" TEST FAILED ✗")
        print("="*60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())

