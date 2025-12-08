"""
공통 데이터 폴더 구조 마이그레이션 스크립트

기존 data 폴더를 새 구조로 마이그레이션:
- data/book/{book_id}/ → data/shared/books/{book_id}/
- data/image/{book_id}/ → data/shared/books/{book_id}/images/
- data/video/{book_id}/ → data/shared/books/{book_id}/videos/
- data/sound/{user_id}/ → data/users/{user_id}/audios/standalone/ (선택적)
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SharedDataMigrator:
    """공통 데이터 마이그레이션 클래스"""
    
    def __init__(self, old_data_path: str, new_data_path: str = None):
        """
        Args:
            old_data_path: 기존 data 폴더 경로 (/Users/byeonsanghun/goinfre/Hack-so42ety/data)
            new_data_path: 새 data 폴더 경로 (기본값: old_data_path와 동일)
        """
        self.old_data_path = Path(old_data_path)
        self.new_data_path = Path(new_data_path) if new_data_path else self.old_data_path
        
        # 마이그레이션 통계
        self.stats = {
            "books_migrated": 0,
            "images_migrated": 0,
            "videos_migrated": 0,
            "metadata_migrated": 0,
            "errors": []
        }
    
    def backup_data(self):
        """데이터 백업"""
        backup_path = self.old_data_path.parent / f"data_backup_{int(os.path.getmtime(self.old_data_path))}"
        if backup_path.exists():
            logger.info(f"Backup already exists: {backup_path}")
            return
        
        logger.info(f"Creating backup: {backup_path}")
        shutil.copytree(self.old_data_path, backup_path)
        logger.info("Backup completed successfully")
    
    def migrate_books(self):
        """책 폴더 마이그레이션"""
        logger.info("Starting book migration...")
        
        old_book_path = self.old_data_path / "book"
        if not old_book_path.exists():
            logger.warning(f"Book path not found: {old_book_path}")
            return
        
        # 새 shared/books 폴더 생성
        shared_books_path = self.new_data_path / "shared" / "books"
        shared_books_path.mkdir(parents=True, exist_ok=True)
        
        # 각 책 폴더 처리
        for book_dir in old_book_path.iterdir():
            if not book_dir.is_dir():
                continue
            
            book_id = book_dir.name
            logger.info(f"Processing book: {book_id}")
            
            try:
                # 새 책 폴더 생성
                new_book_path = shared_books_path / book_id
                new_book_path.mkdir(parents=True, exist_ok=True)
                
                # metadata.json 이동
                metadata_file = book_dir / "metadata.json"
                if metadata_file.exists():
                    shutil.copy2(metadata_file, new_book_path / "metadata.json")
                    self.stats["metadata_migrated"] += 1
                    logger.info(f"  - Migrated metadata.json")
                
                # images 폴더 처리
                self._migrate_book_images(book_id, new_book_path)
                
                # videos 폴더 처리
                self._migrate_book_videos(book_id, new_book_path)
                
                # audios 폴더 처리
                self._migrate_book_audios(book_id, new_book_path)
                
                self.stats["books_migrated"] += 1
                logger.info(f"  ✓ Book {book_id} migrated successfully")
            
            except Exception as e:
                error_msg = f"Error migrating book {book_id}: {str(e)}"
                logger.error(error_msg)
                self.stats["errors"].append(error_msg)
    
    def _migrate_book_images(self, book_id: str, new_book_path: Path):
        """책의 이미지 파일 마이그레이션"""
        old_images_path = self.old_data_path / "image" / book_id
        if not old_images_path.exists():
            logger.warning(f"  - No images found for book {book_id}")
            return
        
        # 새 images 폴더 생성
        new_images_path = new_book_path / "images"
        new_images_path.mkdir(exist_ok=True)
        
        # 이미지 파일 복사
        for img_file in old_images_path.glob("*.png"):
            shutil.copy2(img_file, new_images_path / img_file.name)
            self.stats["images_migrated"] += 1
        
        logger.info(f"  - Migrated {len(list(new_images_path.glob('*.png')))} images")
    
    def _migrate_book_videos(self, book_id: str, new_book_path: Path):
        """책의 비디오 파일 마이그레이션"""
        old_videos_path = self.old_data_path / "video" / book_id
        if not old_videos_path.exists():
            logger.warning(f"  - No videos found for book {book_id}")
            return
        
        # 새 videos 폴더 생성
        new_videos_path = new_book_path / "videos"
        new_videos_path.mkdir(exist_ok=True)
        
        # 비디오 파일 복사
        for vid_file in old_videos_path.glob("*.mp4"):
            shutil.copy2(vid_file, new_videos_path / vid_file.name)
            self.stats["videos_migrated"] += 1
        
        logger.info(f"  - Migrated {len(list(new_videos_path.glob('*.mp4')))} videos")
    
    def _migrate_book_audios(self, book_id: str, new_book_path: Path):
        """책의 오디오 파일 마이그레이션 (metadata.json 기반)"""
        metadata_file = new_book_path / "metadata.json"
        if not metadata_file.exists():
            logger.warning(f"  - No metadata.json found for book {book_id}")
            return
        
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            logger.error(f"  - Error reading metadata.json: {str(e)}")
            return
        
        # 새 audios 폴더 생성
        new_audios_path = new_book_path / "audios"
        new_audios_path.mkdir(exist_ok=True)
        
        audio_count = 0
        # metadata.json의 pages에서 오디오 파일 경로 추출
        for page_idx, page in enumerate(metadata.get("pages", []), 1):
            for dialogue_idx, dialogue in enumerate(page.get("dialogues", []), 1):
                audio_url = dialogue.get("part_audio_url", "")
                if not audio_url:
                    continue
                
                # /data/sound/{user_id}/{audio_file}.mp3 → data/sound/{user_id}/{audio_file}.mp3
                if audio_url.startswith("/data/"):
                    audio_url = audio_url[1:]  # 앞의 "/" 제거
                
                old_audio_path = self.old_data_path.parent / "Hack-so42ety" / audio_url
                if not old_audio_path.exists():
                    # 절대 경로가 아니면 상대 경로로 시도
                    old_audio_path = self.old_data_path.parent / audio_url
                if not old_audio_path.exists():
                    logger.warning(f"  - Audio file not found: {audio_url}")
                    continue
                
                # 새 파일명: page_X_dialogue_Y.mp3
                new_audio_filename = f"page_{page_idx}_dialogue_{dialogue_idx}.mp3"
                new_audio_filepath = new_audios_path / new_audio_filename
                
                shutil.copy2(old_audio_path, new_audio_filepath)
                audio_count += 1
        
        if audio_count > 0:
            logger.info(f"  - Migrated {audio_count} audios")
        else:
            logger.warning(f"  - No audios migrated")
    
    def get_migration_summary(self) -> Dict:
        """마이그레이션 통계 반환"""
        return {
            "total_books": self.stats["books_migrated"],
            "total_images": self.stats["images_migrated"],
            "total_videos": self.stats["videos_migrated"],
            "total_metadata": self.stats["metadata_migrated"],
            "errors": self.stats["errors"],
        }
    
    def get_shared_books_metadata(self) -> List[Dict]:
        """
        마이그레이션된 공통 책의 메타데이터 반환
        DB 마이그레이션 스크립트에서 사용
        """
        shared_books_path = self.new_data_path / "shared" / "books"
        if not shared_books_path.exists():
            return []
        
        books = []
        for book_dir in shared_books_path.iterdir():
            if not book_dir.is_dir():
                continue
            
            metadata_file = book_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        books.append({
                            "book_id": book_dir.name,
                            "metadata": metadata,
                            "path": str(book_dir),
                        })
                except Exception as e:
                    logger.error(f"Error reading metadata for {book_dir.name}: {str(e)}")
        
        return books
    
    def run(self):
        """전체 마이그레이션 실행"""
        logger.info("="*60)
        logger.info("Starting shared data migration")
        logger.info("="*60)
        
        # 1. 백업
        logger.info("\n[Step 1/2] Creating backup...")
        self.backup_data()
        
        # 2. 책 마이그레이션
        logger.info("\n[Step 2/2] Migrating books...")
        self.migrate_books()
        
        # 3. 통계 출력
        logger.info("\n" + "="*60)
        logger.info("Migration Summary")
        logger.info("="*60)
        summary = self.get_migration_summary()
        logger.info(f"Books migrated: {summary['total_books']}")
        logger.info(f"Images migrated: {summary['total_images']}")
        logger.info(f"Videos migrated: {summary['total_videos']}")
        logger.info(f"Metadata files: {summary['total_metadata']}")
        
        if summary['errors']:
            logger.error(f"\nErrors ({len(summary['errors'])}):")
            for error in summary['errors']:
                logger.error(f"  - {error}")
        else:
            logger.info("\n✓ Migration completed successfully with no errors!")
        
        return summary


def main():
    """메인 함수"""
    # 현재 프로젝트의 data 폴더 경로
    old_data_path = "/Users/byeonsanghun/goinfre/Hack-so42ety/data"
    
    migrator = SharedDataMigrator(old_data_path)
    migrator.run()
    
    # 마이그레이션된 책 목록 출력
    books = migrator.get_shared_books_metadata()
    logger.info(f"\nMigrated {len(books)} books:")
    for book in books:
        logger.info(f"  - {book['metadata'].get('title', 'Unknown')} ({book['book_id']})")


if __name__ == "__main__":
    main()

