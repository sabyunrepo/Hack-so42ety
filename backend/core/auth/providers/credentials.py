"""
Credentials Authentication Provider
이메일/비밀번호 인증 (Argon2 전용)
"""

from passlib.context import CryptContext


class CredentialsAuthProvider:
    """
    비밀번호 기반 인증 제공자

    - Argon2id: 비밀번호 해싱 (OWASP 권장, Python 3.12 호환)
    - 보안 표준: Argon2 (2015 Password Hashing Competition 우승)
    """

    # Argon2 전용 컨텍스트
    pwd_context = CryptContext(
        schemes=["argon2"],         # Argon2 단일 알고리즘
        argon2__rounds=4,           # 시간 비용 (약 0.5초)
        argon2__memory_cost=65536,  # 메모리 비용 (64MB)
    )

    @staticmethod
    def hash_password(password: str) -> str:
        """
        비밀번호 해싱 (Argon2id)

        Args:
            password: 평문 비밀번호

        Returns:
            str: Argon2 해시 ($argon2id$v=19$m=65536,t=4,p=1$...)
        """
        return CredentialsAuthProvider.pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        비밀번호 검증 (Argon2)

        Args:
            plain_password: 평문 비밀번호
            hashed_password: Argon2 해시

        Returns:
            bool: 검증 결과
        """
        return CredentialsAuthProvider.pwd_context.verify(
            plain_password, hashed_password
        )
