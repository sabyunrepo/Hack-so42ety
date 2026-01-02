"""
JWT Security Integration Tests
JWT 보안 시나리오 통합 테스트 (만료, 서명 위조, 형식 오류 등)
"""

import pytest
from jose import jwt
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from backend.core.config import settings

# Test Secret Key
TEST_SECRET_KEY = settings.jwt_secret_key
TEST_ALGORITHM = settings.jwt_algorithm


class TestJWTSecurity:
    """JWT 보안 관련 시나리오 테스트"""

    def create_test_token(
        self,
        sub: str = "test_user_id",
        email: str = "test@example.com",
        expires_delta: timedelta = timedelta(minutes=15),
        secret_key: str = TEST_SECRET_KEY,
        algorithm: str = TEST_ALGORITHM,
        token_type: str = "access",
    ) -> str:
        """테스트용 JWT 토큰 생성 헬퍼"""
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode = {
            "sub": sub,
            "email": email,
            "exp": expire,
            "type": token_type,
        }
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
        return encoded_jwt

    @pytest.mark.asyncio
    async def test_access_with_valid_token(self, client: AsyncClient):
        """정상 토큰으로 접근 테스트"""
        token = self.create_test_token()
        
        # 쿠키 설정
        client.cookies.set("access_token", token)
        
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_access_with_expired_token(self, client: AsyncClient):
        """만료된 토큰으로 접근 테스트"""
        # 1분 전 만료된 토큰 생성
        token = self.create_test_token(expires_delta=timedelta(minutes=-1))
        
        client.cookies.set("access_token", token)
        
        response = await client.get("/api/v1/auth/me")
        
        # 401 Unauthorized 기대
        assert response.status_code == 401
        detail = response.json().get("detail", "")
        # 에러 메시지에 expired 관련 내용이 포함될 수 있음 (구현에 따라 다름)
        # AuthenticationException이 발생해야 함

    @pytest.mark.asyncio
    async def test_access_with_invalid_signature(self, client: AsyncClient):
        """잘못된 서명(다른 시크릿 키)으로 생성된 토큰 테스트"""
        # 다른 시크릿 키로 서명
        fake_secret = "invalid-secret-key-for-testing-signature-verification"
        token = self.create_test_token(secret_key=fake_secret)
        
        client.cookies.set("access_token", token)
        
        response = await client.get("/api/v1/auth/me")
        
        # 401 Unauthorized 기대 (서명 검증 실패)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_with_malformed_token(self, client: AsyncClient):
        """형식이 잘못된 토큰 테스트"""
        client.cookies.set("access_token", "not.a.valid.jwt.token")
        
        response = await client.get("/api/v1/auth/me")
        
        # 401 Unauthorized 기대 (디코딩 실패)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_missing_token(self, client: AsyncClient):
        """토큰 없이 접근 테스트"""
        # 쿠키 없이 요청
        client.cookies.clear()
        
        response = await client.get("/api/v1/auth/me")
        
        # 401 Unauthorized 기대
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_with_wrong_token_type(self, client: AsyncClient):
        """Access Token 자리에 Refresh Token 사용 시도"""
        # refresh 타입의 토큰 생성
        token = self.create_test_token(token_type="refresh")
        
        client.cookies.set("access_token", token)
        
        response = await client.get("/api/v1/auth/me")
        
        # 401 Unauthorized 기대 (토큰 타입 불일치)
        # JWTManager.verify_token에서 type 체크를 수행한다고 가정
        assert response.status_code == 401
