"""
Book Repository
동화책 데이터 접근 계층
"""

import uuid
from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.models.book import Book, Page, Dialogue, DialogueTranslation, DialogueAudio
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
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_books(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Book]:
        """
        사용자의 동화책 목록 조회 (다국어 데이터 포함)

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
            .order_by(Book.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

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
        translations: List[dict],  # [{"language_code": "en", "text": "...", "is_primary": True}, ...]
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
        dialogue = Dialogue(
            page_id=page_id,
            speaker=speaker,
            sequence=sequence
        )
        self.session.add(dialogue)
        await self.session.flush()

        # 번역 추가
        for trans_data in translations:
            translation = DialogueTranslation(
                dialogue_id=dialogue.id,
                language_code=trans_data["language_code"],
                text=trans_data["text"],
                is_primary=trans_data.get("is_primary", False)
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
        duration: Optional[float] = None
    ) -> DialogueAudio:
        """
        대사 오디오 추가

        Args:
            dialogue_id: 대사 UUID
            language_code: 언어 코드
            voice_id: 음성 ID
            audio_url: 오디오 파일 URL
            duration: 재생 시간 (초)

        Returns:
            DialogueAudio: 생성된 오디오
        """
        audio = DialogueAudio(
            dialogue_id=dialogue_id,
            language_code=language_code,
            voice_id=voice_id,
            audio_url=audio_url,
            duration=duration
        )
        self.session.add(audio)
        await self.session.flush()
        await self.session.refresh(audio)
        return audio
