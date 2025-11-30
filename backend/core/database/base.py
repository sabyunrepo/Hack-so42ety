"""
Database Base Class
모든 ORM 모델의 베이스 클래스
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    SQLAlchemy Base Class

    모든 ORM 모델은 이 클래스를 상속받아야 함
    """
    pass
