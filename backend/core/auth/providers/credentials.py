"""
Credentials Authentication Provider
이메일/비밀번호 인증
"""

from passlib.context import CryptContext


class CredentialsAuthProvider:
    """
    비밀번호 기반 인증 제공자

    bcrypt를 사용한 비밀번호 해싱 및 검증
    """

    # bcrypt 컨텍스트 (rounds=12)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    def hash_password(password: str) -> str:
        """
        비밀번호 해싱 (bcrypt)

        Args:
            password: 평문 비밀번호

        Returns:
            str: 해싱된 비밀번호
        """
        return CredentialsAuthProvider.pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        비밀번호 검증

        Args:
            plain_password: 평문 비밀번호
            hashed_password: 해싱된 비밀번호

        Returns:
            bool: 검증 결과
        """
        return CredentialsAuthProvider.pwd_context.verify(
            plain_password, hashed_password
        )
