#!/usr/bin/env python3
"""
Update image URLs in the pages table to remove :8000 port number
Usage: python update_image_urls.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from infrastructure.database.connection import get_db


async def update_image_urls():
    """Remove :8000 from all image_url entries in pages table"""

    async for session in get_db():
        try:
            # Preview the changes
            preview_query = text("""
                SELECT
                    id,
                    image_url AS old_url,
                    REPLACE(image_url, ':8000', '') AS new_url
                FROM pages
                WHERE image_url LIKE '%:8000%'
            """)

            result = await session.execute(preview_query)
            rows = result.fetchall()

            if not rows:
                print("No URLs found with :8000 port number.")
                return

            print(f"\nFound {len(rows)} URLs to update:")
            print("-" * 80)
            for row in rows[:5]:  # Show first 5 examples
                print(f"Old: {row.old_url}")
                print(f"New: {row.new_url}")
                print("-" * 80)

            if len(rows) > 5:
                print(f"... and {len(rows) - 5} more rows\n")

            # Ask for confirmation
            confirm = input(f"\nUpdate {len(rows)} rows? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Update cancelled.")
                return

            # Perform the update
            update_query = text("""
                UPDATE pages
                SET image_url = REPLACE(image_url, ':8000', ''),
                    updated_at = NOW()
                WHERE image_url LIKE '%:8000%'
            """)

            result = await session.execute(update_query)
            await session.commit()

            print(f"\n✅ Successfully updated {result.rowcount} rows")

            # Verify the changes
            verify_query = text("""
                SELECT COUNT(*) as count
                FROM pages
                WHERE image_url LIKE '%:8000%'
            """)

            result = await session.execute(verify_query)
            remaining = result.scalar()

            if remaining == 0:
                print("✅ Verification passed: No URLs with :8000 remaining")
            else:
                print(f"⚠️  Warning: {remaining} URLs still contain :8000")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error updating URLs: {e}")
            raise
        finally:
            await session.close()
            break


if __name__ == "__main__":
    print("=" * 80)
    print("Image URL Update Script")
    print("=" * 80)
    print("This will remove ':8000' from all image_url entries in the pages table")
    print("=" * 80)

    asyncio.run(update_image_urls())
