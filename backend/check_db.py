import asyncio
import sys
sys.path.append("/app")
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings
from backend.domain.models.book import Book
from backend.domain.models.user import User

async def check_books():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(select(Book))
        books = result.scalars().all()
        print(f"Total books found: {len(books)}")
        for book in books:
            print(f"Book: {book.title}, ID: {book.id}, UserID: {book.user_id}, is_default: {book.is_default}")

    await engine.dispose()

# Added function to check users
async def check_users():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"Found {len(users)} users:")
        for user in users:
            print(f"- {user.email} (ID: {user.id})")
    
    await engine.dispose()

# Added main function to run both checks
async def main():
    await check_books()
    await check_users()

if __name__ == "__main__":
    asyncio.run(main())
