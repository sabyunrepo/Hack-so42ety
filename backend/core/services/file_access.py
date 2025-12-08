"""
File Access Control Service
파일 접근 제어 서비스

책의 공개/비공개 설정에 따라 파일 접근 권한을 확인합니다.
"""
import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from backend.features.storybook.models import Book
from backend.features.storybook.repository import BookRepository
from backend.core.database.session import get_db

logger = logging.getLogger(__name__)


class FileAccessService:
    """
    파일 접근 제어 서비스
    
    파일 경로에서 책 정보를 추출하고 접근 권한을 확인합니다.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.book_repo = BookRepository(db_session)
    
    def _extract_book_id_from_path(self, file_path: str) -> Optional[uuid.UUID]:
        """
        파일 경로에서 책 ID 추출
        
        경로 형식: users/{user_id}/books/{book_id}/images/page_1.png
        또는: users/{user_id}/books/{book_id}/audios/page_1.mp3
        
        Args:
            file_path: 파일 경로
        
        Returns:
            Optional[uuid.UUID]: 책 ID 또는 None
        """
        try:
            # 경로 파싱
            parts = file_path.split('/')
            
            # users/{user_id}/books/{book_id}/... 형식 확인
            if len(parts) >= 4 and parts[0] == 'users' and parts[2] == 'books':
                book_id_str = parts[3]
                return uuid.UUID(book_id_str)
            
            # 기존 형식: books/{book_id}/... (하위 호환성)
            if len(parts) >= 2 and parts[0] == 'books':
                book_id_str = parts[1]
                return uuid.UUID(book_id_str)
            
            return None
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to extract book_id from path {file_path}: {e}")
            return None
    
    async def check_file_access(
        self,
        file_path: str,
        current_user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        파일 접근 권한 확인
        
        Args:
            file_path: 파일 경로
            current_user_id: 현재 사용자 ID (None이면 비인증 사용자)
        
        Returns:
            bool: 접근 허용 여부
        
        Raises:
            FileNotFoundError: 파일이 존재하지 않거나 책을 찾을 수 없음
            PermissionDenied: 접근 권한이 없음
        """
        # 파일 경로에서 책 ID 추출
        book_id = self._extract_book_id_from_path(file_path)
        
        if not book_id:
            # 책 ID를 추출할 수 없는 경우 (예: standalone audio)
            # 소유자만 접근 가능 (user_id로 확인)
            if current_user_id:
                # 경로에서 user_id 추출
                parts = file_path.split('/')
                if len(parts) >= 2 and parts[0] == 'users':
                    try:
                        path_user_id = uuid.UUID(parts[1])
                        if path_user_id == current_user_id:
                            return True
                    except (ValueError, IndexError):
                        pass
            
            # 비인증 사용자는 접근 불가
            if not current_user_id:
                raise PermissionError("File access requires authentication")
            
            # 인증된 사용자도 소유자가 아니면 접근 불가
            raise PermissionError("File access denied")
        
        # 책 정보 조회
        book = await self.book_repo.get(book_id)
        
        if not book:
            raise FileNotFoundError(f"Book not found: {book_id}")
        
        # 공개 책: 모든 사용자 접근 가능
        if book.is_public or book.visibility == "public":
            return True
        
        # 비공개 책: 소유자만 접근 가능
        if current_user_id and book.user_id == current_user_id:
            return True
        
        # 접근 거부
        raise PermissionError(f"Access denied to book {book_id}")

