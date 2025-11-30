import asyncio
import sys
sys.path.append("/app")
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings
from backend.domain.models.user import User
from backend.core.auth.providers.credentials import CredentialsAuthProvider
import uuid

async def create_user():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    provider = CredentialsAuthProvider()

    async with async_session() as session:
        # Check if user exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == "test@example.com"))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("User test@example.com already exists.")
        else:
            new_user = User(
                id=uuid.uuid4(),
                email="test@example.com",
                password_hash=provider.hash_password("password123"),
                is_active=True,
                oauth_provider="email"
            )
            session.add(new_user)
            await session.commit()
            print("Created user test@example.com / password123")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_user())
