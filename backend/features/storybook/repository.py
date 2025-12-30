"""
Book Repository
동화책 데이터 접근 계층
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Book, Page, Dialogue, DialogueTranslation, DialogueAudio
from backend.domain.repositories.base import AbstractRepository


class BookRepository(AbstractRepository[Book]):
    """
    동화책 Repository

    Book, Page, Dialogue 엔티티 관리
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, Book)

    async def get_with_pages(self, book_id: uuid.UUID) -> Optional[Book]:
        """
        동화책 상세 조회 (페이지, 대사, 번역, 오디오 포함)

        ✅ Readonly 보장: 세션에서 분리하여 반환 (DB 수정 방지)

        Args:
            book_id: 동화책 UUID

        Returns:
            Optional[Book]: 동화책 (페이지 및 다국어 데이터 포함) 또는 None
        """
        query = (
            select(Book)
            .options(
                selectinload(Book.pages)
                .selectinload(Page.dialogues)
                .selectinload(Dialogue.translations)
            )
            .options(
                selectinload(Book.pages)
                .selectinload(Page.dialogues)
                .selectinload(Dialogue.audios)
            )
            .where(Book.id == book_id)
            .execution_options(populate_existing=False)  # 캐시 사용
        )
        result = await self.session.execute(query)
        book = result.scalar_one_or_none()

        if book:
            # ✅ 세션에서 완전히 분리 (읽기 전용 보장)
            self._detach_book_from_session(book)

        return book

    async def get_user_books(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Book]:
        """
        사용자의 동화책 목록 조회 (다국어 데이터 포함)

        ✅ Readonly 보장: 세션에서 분리하여 반환 (DB 수정 방지)

        Args:
            user_id: 사용자 UUID
            skip: 건너뛸 개수
            limit: 가져올 개수

        Returns:
            List[Book]: 동화책 목록
        """
        query = (
            select(Book)
            .options(
                selectinload(Book.pages)
                .selectinload(Page.dialogues)
                .selectinload(Dialogue.translations)
            )
            .options(
                selectinload(Book.pages)
                .selectinload(Page.dialogues)
                .selectinload(Dialogue.audios)
            )
            .where(or_(Book.user_id == user_id, Book.is_default == True))
            .where(Book.is_deleted == False)  # 삭제된 책 제외
            .order_by(Book.created_at.asc())
            .offset(skip)
            .limit(limit)
            .execution_options(populate_existing=False)  # 캐시 사용
        )
        result = await self.session.execute(query)
        books = list(result.scalars().all())

        # ✅ 모든 책을 세션에서 분리 (읽기 전용 보장)
        for book in books:
            self._detach_book_from_session(book)

        return books

    async def count_user_created_books(self, user_id: uuid.UUID) -> int:
        """
        사용자가 생성한 책 개수만 카운트 (샘플 제외)

        Args:
            user_id: 사용자 UUID

        Returns:
            int: 사용자가 생성한 책 개수
        """
        query = (
            select(func.count())
            .select_from(Book)
            .where(Book.user_id == user_id)
            .where(Book.is_default == False)
            .where(Book.is_deleted == False)  # 삭제된 책 제외
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_user_books_summary(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Book]:
        """
        사용자의 동화책 목록 조회 (목록용, 페이지 정보 제외)

        ✅ Readonly 보장: 세션에서 분리하여 반환 (DB 수정 방지)

        Args:
            user_id: 사용자 UUID
            skip: 건너뛸 개수
            limit: 가져올 개수

        Returns:
            List[Book]: 동화책 목록 (페이지 정보 미포함)
        """
        from sqlalchemy import inspect

        query = (
            select(Book)
            .where(or_(Book.user_id == user_id, Book.is_default == True))
            .where(Book.is_deleted == False)  # 삭제된 책 제외
            .order_by(Book.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        books = list(result.scalars().all())

        # ✅ 모든 책을 세션에서 분리 (읽기 전용 보장)
        # 페이지 정보 없으므로 Book만 분리 (_detach_book_from_session은 pages 접근하여 사용 불가)
        for book in books:
            if inspect(book).session is not None:
                self.session.expunge(book)

        return books

    async def add_page(self, book_id: uuid.UUID, page_data: dict) -> Page:
        """
        페이지 추가

        Args:
            book_id: 동화책 UUID
            page_data: 페이지 데이터 (sequence, image_prompt 등)

        Returns:
            Page: 생성된 페이지
        """
        page = Page(book_id=book_id, **page_data)
        self.session.add(page)
        await self.session.flush()
        await self.session.refresh(page)
        return page

    async def add_dialogue(self, page_id: uuid.UUID, dialogue_data: dict) -> Dialogue:
        """
        대사 추가 (DEPRECATED: 하위 호환성을 위해 유지)

        Args:
            page_id: 페이지 UUID
            dialogue_data: 대사 데이터 (sequence, speaker, text_en 등)

        Returns:
            Dialogue: 생성된 대사
        """
        dialogue = Dialogue(page_id=page_id, **dialogue_data)
        self.session.add(dialogue)
        await self.session.flush()
        await self.session.refresh(dialogue)
        return dialogue

    async def add_dialogue_with_translation(
        self,
        page_id: uuid.UUID,
        speaker: str,
        sequence: int,
        translations: List[
            dict
        ],  # [{"language_code": "en", "text": "...", "is_primary": True}, ...]
    ) -> Dialogue:
        """
        대사 추가 (다국어 번역 포함)

        Args:
            page_id: 페이지 UUID
            speaker: 화자
            sequence: 대사 순서
            translations: 번역 목록 [{"language_code": "en", "text": "...", "is_primary": True}, ...]

        Returns:
            Dialogue: 생성된 대사 (번역 포함)
        """
        dialogue = Dialogue(page_id=page_id, speaker=speaker, sequence=sequence)
        self.session.add(dialogue)
        await self.session.flush()

        # 번역 추가
        for trans_data in translations:
            translation = DialogueTranslation(
                dialogue_id=dialogue.id,
                language_code=trans_data["language_code"],
                text=trans_data["text"],
                is_primary=trans_data.get("is_primary", False),
            )
            self.session.add(translation)

        await self.session.flush()
        await self.session.refresh(dialogue)
        return dialogue

    async def add_dialogue_audio(
        self,
        dialogue_id: uuid.UUID,
        language_code: str,
        voice_id: str,
        audio_url: str,
        duration: Optional[float] = None,
        status: str = "PENDING",
    ) -> DialogueAudio:
        """
        대사 오디오 추가

        Args:
            dialogue_id: 대사 UUID
            language_code: 언어 코드
            voice_id: 음성 ID
            audio_url: 오디오 파일 URL
            duration: 재생 시간 (초)
            status: 오디오 생성 상태 (PENDING, PROCESSING, COMPLETED, FAILED)

        Returns:
            DialogueAudio: 생성된 오디오
        """
        audio = DialogueAudio(
            dialogue_id=dialogue_id,
            language_code=language_code,
            voice_id=voice_id,
            audio_url=audio_url,
            duration=duration,
            status=status,
        )
        self.session.add(audio)
        await self.session.flush()
        await self.session.refresh(audio)
        return audio

    # ==================== Progress Tracking Methods ====================

    async def update_progress(
        self,
        book_id: uuid.UUID,
        pipeline_stage: Optional[str] = None,
        progress_percentage: Optional[int] = None,
        task_metadata: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Book]:
        """
        비동기 파이프라인 진행 상황 업데이트

        Args:
            book_id: Book UUID
            pipeline_stage: 파이프라인 단계 (story|images|tts|video|finalizing|completed|failed)
            progress_percentage: 진행률 (0-100)
            task_metadata: Task 메타데이터 (JSONB)
            error_message: 에러 메시지

        Returns:
            Optional[Book]: 업데이트된 Book, 없으면 None
        """
        update_data = {}

        if pipeline_stage is not None:
            update_data["pipeline_stage"] = pipeline_stage

        if progress_percentage is not None:
            update_data["progress_percentage"] = progress_percentage

        if task_metadata is not None:
            update_data["task_metadata"] = task_metadata

        if error_message is not None:
            update_data["error_message"] = error_message

        if not update_data:
            # 업데이트할 데이터가 없으면 현재 Book 반환
            return await self.get(book_id)

        return await self.update(book_id, **update_data)

    async def get_progress(self, book_id: uuid.UUID) -> Optional[dict]:
        """
        Book 생성 진행 상황 조회

        Args:
            book_id: Book UUID

        Returns:
            Optional[dict]: 진행 상황 정보
                {
                    "status": "creating|completed|failed",
                    "pipeline_stage": "story|images|tts|video|completed",
                    "progress_percentage": 0-100,
                    "task_metadata": {...},
                    "error_message": str | None,
                    "title": str,
                    "created_at": datetime,
                }
            Book이 없으면 None
        """
        book = await self.get(book_id)

        if not book:
            return None

        return {
            "status": book.status,
            "pipeline_stage": book.pipeline_stage,
            "progress_percentage": book.progress_percentage,
            "task_metadata": book.task_metadata,
            "error_message": book.error_message,
            "retry_count": book.retry_count,
            "title": book.title,
            "created_at": book.created_at,
            "updated_at": book.updated_at,
        }

    # ==================== Quota Management Methods ====================

    async def count_active_books(self, user_id: uuid.UUID) -> int:
        """
        사용자의 활성(삭제되지 않은) 도서 개수를 계산합니다.

        Args:
            user_id: 사용자 UUID

        Returns:
            int: 활성 도서의 개수
        """
        query = select(func.count(Book.id)).where(
            Book.user_id == user_id,
            Book.is_deleted == False,  # 삭제되지 않은 도서만 계산
        )
        result = await self.session.execute(query)
        # 결과가 없을 경우 안전하게 0을 반환
        return result.scalar() or 0

    async def soft_delete(self, book_id: uuid.UUID) -> bool:
        """
        도서를 소프트 삭제합니다 (AbstractRepository의 update() 사용).

        Args:
            book_id: Book UUID

        Returns:
            bool: 성공적으로 업데이트되었으면 True, 도서가 발견되지 않았으면 False
        """
        # AbstractRepository의 update 메서드를 호출하여 is_deleted와 deleted_at을 업데이트합니다.
        updated_book = await self.update(
            book_id, is_deleted=True, deleted_at=datetime.utcnow()
        )

        # update()는 객체를 찾지 못하면 None을 반환하므로, None이 아니면 성공으로 간주합니다.
        return updated_book

    def _detach_book_from_session(self, book: Book) -> None:
        """
        Book 객체와 모든 연관 객체를 세션에서 분리 (Readonly 보장)

        Args:
            book: 분리할 Book 객체
        """
        from sqlalchemy import inspect

        # Book 객체 분리
        if inspect(book).session is not None:
            self.session.expunge(book)

        # 연관된 모든 객체 분리
        for page in book.pages:
            if inspect(page).session is not None:
                self.session.expunge(page)

            for dialogue in page.dialogues:
                if inspect(dialogue).session is not None:
                    self.session.expunge(dialogue)

                # 번역 분리
                for translation in dialogue.translations:
                    if inspect(translation).session is not None:
                        self.session.expunge(translation)

                # 오디오 분리
                for audio in dialogue.audios:
                    if inspect(audio).session is not None:
                        self.session.expunge(audio)
