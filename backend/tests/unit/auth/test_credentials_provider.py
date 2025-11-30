"""
Credentials Provider Unit Tests
비밀번호 해싱 및 검증 테스트
"""

import pytest

from backend.core.auth.providers.credentials import CredentialsAuthProvider


class TestCredentialsAuthProvider:
    """Credentials Auth Provider 단위 테스트"""

    def test_hash_password(self):
        """비밀번호 해싱 테스트"""
        password = "test_password_123"
        hashed = CredentialsAuthProvider.hash_password(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password  # 해시는 원본과 달라야 함
        assert len(hashed) > 0

    def test_hash_password_different_outputs(self):
        """같은 비밀번호도 매번 다른 해시 생성 (salt)"""
        password = "test_password_123"
        hash1 = CredentialsAuthProvider.hash_password(password)
        hash2 = CredentialsAuthProvider.hash_password(password)

        assert hash1 != hash2  # bcrypt salt로 인해 다른 해시

    def test_verify_password_correct(self):
        """올바른 비밀번호 검증 테스트"""
        password = "correct_password"
        hashed = CredentialsAuthProvider.hash_password(password)

        result = CredentialsAuthProvider.verify_password(password, hashed)

        assert result is True

    def test_verify_password_incorrect(self):
        """잘못된 비밀번호 검증 테스트"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = CredentialsAuthProvider.hash_password(password)

        result = CredentialsAuthProvider.verify_password(wrong_password, hashed)

        assert result is False

    def test_verify_password_empty(self):
        """빈 비밀번호 검증 테스트"""
        password = "test_password"
        hashed = CredentialsAuthProvider.hash_password(password)

        result = CredentialsAuthProvider.verify_password("", hashed)

        assert result is False

    def test_hash_special_characters(self):
        """특수문자 포함 비밀번호 해싱"""
        password = "P@ssw0rd!#$%^&*()"
        hashed = CredentialsAuthProvider.hash_password(password)

        assert hashed is not None
        assert CredentialsAuthProvider.verify_password(password, hashed) is True

    def test_hash_unicode_password(self):
        """유니코드 비밀번호 해싱"""
        password = "비밀번호1234!"
        hashed = CredentialsAuthProvider.hash_password(password)

        assert hashed is not None
        assert CredentialsAuthProvider.verify_password(password, hashed) is True

    def test_verify_invalid_hash_format(self):
        """잘못된 해시 형식 검증"""
        password = "test_password"
        invalid_hash = "not_a_valid_hash"

        # bcrypt가 ValueError 발생시킴
        result = CredentialsAuthProvider.verify_password(password, invalid_hash)
        assert result is False
