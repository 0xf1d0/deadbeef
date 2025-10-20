"""
Migration script to move authentication data from config.json to database.
Run this script once to migrate existing user data.
"""
import asyncio
import json
from sqlalchemy import select

from db import AsyncSessionLocal, init_db
from db.models import AuthenticatedUser, Professional, ProfessionalCourseChannel


async def migrate():
    """Migrate authentication data from config.json to database."""
    print("Starting authentication data migration...")
    
    # Initialize database
    await init_db()
    print("✓ Database initialized")
    
    # Load config.json
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    users = config.get('users', [])
    print(f"Found {len(users)} users in config.json")
    
    if not users:
        print("No users to migrate.")
        return
    
    async with AsyncSessionLocal() as session:
        migrated_students = 0
        migrated_professionals = 0
        skipped = 0
        
        for user_data in users:
            user_id = user_data.get('id')
            email = user_data.get('email')
            
            if not user_id or not email:
                print(f"⚠ Skipping incomplete user record: {user_data}")
                skipped += 1
                continue
            
            # Check if user already exists
            result = await session.execute(
                select(AuthenticatedUser).where(AuthenticatedUser.user_id == user_id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"⚠ User {user_id} already exists, skipping")
                skipped += 1
                continue
            
            # Determine user type based on data structure
            is_student = 'studentId' in user_data and user_data['studentId']
            is_professional = 'courses' in user_data and isinstance(user_data['courses'], list) and user_data['courses']
            
            if is_student:
                # Create student user
                auth_user = AuthenticatedUser(
                    user_id=user_id,
                    email=email,
                    user_type='student',
                    student_id=user_data.get('studentId'),
                    rootme_id=user_data.get('rootme'),
                    linkedin_url=user_data.get('linkedin')
                )
                session.add(auth_user)
                migrated_students += 1
                print(f"✓ Migrated student: {email} (ID: {user_id})")
                
            elif is_professional:
                # Check if professional record exists
                result = await session.execute(
                    select(Professional).where(Professional.email == email)
                )
                pro = result.scalar_one_or_none()
                
                if not pro:
                    # Create professional record
                    pro = Professional(email=email)
                    session.add(pro)
                    await session.flush()  # Get the ID
                    
                    # Add course channels
                    for channel_id in user_data['courses']:
                        course_channel = ProfessionalCourseChannel(
                            professional_id=pro.id,
                            channel_id=channel_id
                        )
                        session.add(course_channel)
                
                # Create authenticated user
                auth_user = AuthenticatedUser(
                    user_id=user_id,
                    email=email,
                    user_type='professional',
                    rootme_id=user_data.get('rootme'),
                    linkedin_url=user_data.get('linkedin')
                )
                session.add(auth_user)
                migrated_professionals += 1
                print(f"✓ Migrated professional: {email} (ID: {user_id})")
            
            else:
                print(f"⚠ Could not determine user type for {email}, skipping")
                skipped += 1
        
        await session.commit()
    
    print("\n" + "="*50)
    print("Migration Complete!")
    print(f"✓ Students migrated: {migrated_students}")
    print(f"✓ Professionals migrated: {migrated_professionals}")
    print(f"⚠ Skipped: {skipped}")
    print("="*50)
    
    print("\n⚠ Important: The 'users' array in config.json is still present.")
    print("   Review the migrated data in the database, then you can manually")
    print("   remove the 'users' array from config.json if everything looks good.")


if __name__ == '__main__':
    asyncio.run(migrate())

