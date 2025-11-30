import asyncio
import json
import os
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import sys

# Backend path setup
sys.path.append("/app")

from backend.core.config import settings
from backend.domain.models.book import Book, Page, Dialogue
from backend.domain.models.user import User

# Backup Data Path (Inside Docker)
BACKUP_DIR = "/app/backup_data"
TARGET_DATA_DIR = "/app/data"

async def migrate():
    print("Starting migration...")
    
    # Database connection
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Get or Create Admin User for ownership
        admin_email = "admin@moriai.com"
        result = await session.execute(
            text(f"SELECT id FROM users WHERE email = '{admin_email}'")
        )
        admin_user_id = result.scalar_one_or_none()
        
        if not admin_user_id:
            print("Creating admin user...")
            admin_user = User(
                email=admin_email,
                password_hash="admin_hash_placeholder", # Not used for login
                oauth_provider="system",
                oauth_id="system_admin"
            )
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            admin_user_id = admin_user.id

        # 2. Iterate Backup Books
        book_backup_dir = Path(BACKUP_DIR) / "book"
        if not book_backup_dir.exists():
            print(f"Backup directory not found: {book_backup_dir}")
            return

        for book_dir in book_backup_dir.iterdir():
            if not book_dir.is_dir():
                continue
            
            metadata_path = book_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            print(f"Processing book: {book_dir.name}")
            with open(metadata_path, "r") as f:
                data = json.load(f)

            # 3. Create Book
            book_id = uuid.UUID(data["id"])
            
            # Check if exists
            existing = await session.get(Book, book_id)
            if existing:
                print(f"Book {book_id} already exists. Skipping.")
                continue

            # Copy Cover Image
            cover_rel_path = "/".join(data["cover_image"].strip("/").split("/")[1:])
            cover_src = Path(BACKUP_DIR) / cover_rel_path
            
            cover_dest_rel = f"image/{book_id}/{Path(data['cover_image']).name}"
            cover_dest = Path(TARGET_DATA_DIR) / cover_dest_rel
            
            if cover_src.exists():
                os.makedirs(cover_dest.parent, exist_ok=True)
                shutil.copy2(cover_src, cover_dest)
                cover_url = f"{settings.storage_base_url}/image/{book_id}/{Path(data['cover_image']).name}"
            else:
                print(f"Warning: Cover image not found at {cover_src}")
                cover_url = None

            book = Book(
                id=book_id,
                user_id=admin_user_id,
                title=data["title"],
                cover_image=cover_url,
                status="completed",
                is_default=True,
                created_at=datetime.fromisoformat(data["created_at"])
            )
            session.add(book)
            
            # 4. Create Pages & Dialogues
            for page_data in data["pages"]:
                page_id = uuid.UUID(page_data["id"])
                
                # Copy Page Content (Image/Video)
                content_url = None
                if page_data.get("content"):
                    rel_path = "/".join(page_data["content"].strip("/").split("/")[1:])
                    src_path = Path(BACKUP_DIR) / rel_path
                    
                    dest_rel = rel_path 
                    dest_path = Path(TARGET_DATA_DIR) / dest_rel
                    
                    if src_path.exists():
                        os.makedirs(dest_path.parent, exist_ok=True)
                        shutil.copy2(src_path, dest_path)
                        content_url = f"{settings.storage_base_url}/{rel_path}"
                    else:
                        print(f"Warning: Content file not found at {src_path}")

                # Copy Fallback Image
                fallback_url = None
                if page_data.get("fallback_image"):
                    rel_path = "/".join(page_data["fallback_image"].strip("/").split("/")[1:])
                    src_path = Path(BACKUP_DIR) / rel_path
                    dest_path = Path(TARGET_DATA_DIR) / rel_path
                    
                    if src_path.exists():
                        os.makedirs(dest_path.parent, exist_ok=True)
                        shutil.copy2(src_path, dest_path)
                        fallback_url = f"{settings.storage_base_url}/{rel_path}"

                page = Page(
                    id=page_id,
                    book_id=book_id,
                    sequence=page_data["index"],
                    image_url=content_url if page_data["type"] == "image" else fallback_url,
                )
                if page_data["type"] == "video":
                     page.image_url = content_url
                
                session.add(page)

                # Dialogues
                for diag_data in page_data["dialogues"]:
                    diag_id = uuid.UUID(diag_data["id"])
                    
                    # Copy Audio
                    audio_url = None
                    if diag_data.get("part_audio_url"):
                        rel_path = "/".join(diag_data["part_audio_url"].strip("/").split("/")[1:])
                        src_path = Path(BACKUP_DIR) / rel_path
                        dest_path = Path(TARGET_DATA_DIR) / rel_path
                        
                        if src_path.exists():
                            os.makedirs(dest_path.parent, exist_ok=True)
                            shutil.copy2(src_path, dest_path)
                            audio_url = f"{settings.storage_base_url}/{rel_path}"

                    dialogue = Dialogue(
                        id=diag_id,
                        page_id=page_id,
                        sequence=diag_data["index"],
                        speaker="Narrator",
                        text_en=diag_data["text"],
                        audio_url=audio_url
                    )
                    session.add(dialogue)

            await session.commit()
            print(f"Successfully migrated book: {data['title']}")

    await engine.dispose()
    print("Migration completed.")

if __name__ == "__main__":
    asyncio.run(migrate())
