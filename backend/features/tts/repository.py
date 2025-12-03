from sqlalchemy.ext.asyncio import AsyncSession
from .models import Audio
from backend.domain.repositories.base import AbstractRepository

class AudioRepository(AbstractRepository[Audio]):
    """
    오디오 레포지토리
    """
    def __init__(self, session: AsyncSession):
        super().__init__(session, Audio)
