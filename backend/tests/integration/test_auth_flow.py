"""
Auth Flow Integration Tests
인증 플로우 통합 테스트 (DB 연동)
"""

import pytest
from httpx import AsyncClient, Cookies
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.auth.models import User
from backend.features.auth.repository import UserRepository


class TestAuthRegistrationFlow:
    """회원가입 플로우 통합 테스트"""

    @pytest.mark.asyncio
    async def test_register_new_user(self, client: AsyncClient, db_session: AsyncSession):
        """신규 사용자 회원가입 테스트"""
        payload = {"email": "newuser@example.com", "password": "password123"}

        response = await client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == 201
        data = response.json()
        # 토큰은 httpOnly 쿠키에 저장되므로 응답 본문에 없음
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["is_active"] is True

        # httpOnly 쿠키 확인
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert response.cookies["access_token"] is not None
        assert response.cookies["refresh_token"] is not None

        # DB에 실제 생성되었는지 확인
        user_repo = UserRepository(db_session)
        user = await user_repo.get_by_email("newuser@example.com")
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.password_hash is not None

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """중복 이메일 회원가입 실패 테스트"""
        # 첫 번째 회원가입
        payload = {"email": "duplicate@example.com", "password": "password123"}
        await client.post("/api/v1/auth/register", json=payload)

        # 같은 이메일로 재시도
        response = await client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """잘못된 이메일 형식 테스트"""
        payload = {"email": "not-an-email", "password": "password123"}

        response = await client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """짧은 비밀번호 테스트"""
        payload = {"email": "test@example.com", "password": "short"}

        response = await client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == 422  # Validation error


class TestAuthLoginFlow:
    """로그인 플로우 통합 테스트"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, db_session: AsyncSession):
        """정상 로그인 테스트"""
        # 먼저 회원가입
        register_payload = {"email": "logintest@example.com", "password": "password123"}
        await client.post("/api/v1/auth/register", json=register_payload)

        # 로그인 시도
        login_payload = {"email": "logintest@example.com", "password": "password123"}
        response = await client.post("/api/v1/auth/login", json=login_payload)

        assert response.status_code == 200
        data = response.json()
        # 토큰은 httpOnly 쿠키에 저장되므로 응답 본문에 없음
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert data["user"]["email"] == "logintest@example.com"

        # httpOnly 쿠키 확인
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """잘못된 비밀번호 로그인 테스트"""
        # 회원가입
        await client.post(
            "/api/v1/auth/register",
            json={"email": "wrongpass@example.com", "password": "correctpass"},
        )

        # 잘못된 비밀번호로 로그인
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrongpass@example.com", "password": "wrongpass"},
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """존재하지 않는 사용자 로그인 테스트"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_oauth_user_with_password(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """OAuth 전용 사용자가 비밀번호로 로그인 시도"""
        # OAuth 사용자 생성
        user_repo = UserRepository(db_session)
        oauth_user = User(
            email="oauth@example.com",
            password_hash=None,  # OAuth 전용
            oauth_provider="google",
            oauth_id="google123",
        )
        await user_repo.create(oauth_user)

        # 비밀번호로 로그인 시도
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "oauth@example.com", "password": "anypassword"},
        )

        assert response.status_code == 400
        assert "google" in response.json()["detail"].lower()


class TestAuthGoogleOAuthFlow:
    """Google OAuth 플로우 통합 테스트"""

    @pytest.mark.asyncio
    async def test_google_oauth_new_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Google OAuth 신규 사용자 테스트"""
        # Mock Google token verification
        from unittest.mock import patch

        mock_user_info = {
            "sub": "google_new_123",
            "email": "newgoogle@gmail.com",
            "name": "Google User",
            "picture": "https://example.com/photo.jpg",
        }

        with patch(
            "backend.core.auth.providers.google_oauth.id_token.verify_oauth2_token",
            return_value=mock_user_info,
        ):
            response = await client.post(
                "/api/v1/auth/google", json={"token": "valid_google_token"}
            )

        assert response.status_code == 200
        data = response.json()
        # 토큰은 httpOnly 쿠키에 저장되므로 응답 본문에 없음
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert data["user"]["email"] == "newgoogle@gmail.com"

        # httpOnly 쿠키 확인
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

        # DB에 생성되었는지 확인
        user_repo = UserRepository(db_session)
        user = await user_repo.get_by_oauth("google", "google_new_123")
        assert user is not None
        assert user.oauth_provider == "google"
        assert user.password_hash is None  # OAuth 전용

    @pytest.mark.asyncio
    async def test_google_oauth_existing_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Google OAuth 기존 사용자 로그인 테스트"""
        # 기존 OAuth 사용자 생성
        user_repo = UserRepository(db_session)
        existing_user = User(
            email="existing@gmail.com",
            oauth_provider="google",
            oauth_id="google_existing_456",
        )
        await user_repo.create(existing_user)

        # Mock verification
        from unittest.mock import patch

        mock_user_info = {
            "sub": "google_existing_456",
            "email": "existing@gmail.com",
            "name": "Existing User",
        }

        with patch(
            "backend.core.auth.providers.google_oauth.id_token.verify_oauth2_token",
            return_value=mock_user_info,
        ):
            response = await client.post(
                "/api/v1/auth/google", json={"token": "valid_token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "existing@gmail.com"

    @pytest.mark.asyncio
    async def test_google_oauth_invalid_token(self, client: AsyncClient):
        """Google OAuth 잘못된 토큰 테스트"""
        from unittest.mock import patch

        with patch(
            "backend.core.auth.providers.google_oauth.id_token.verify_oauth2_token",
            side_effect=ValueError("Invalid token"),
        ):
            response = await client.post(
                "/api/v1/auth/google", json={"token": "invalid_token"}
            )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()


class TestAuthRefreshTokenFlow:
    """토큰 갱신 플로우 통합 테스트"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Refresh Token으로 Access Token 갱신"""
        # 회원가입으로 토큰 획득 (쿠키로 설정됨)
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "refresh@example.com", "password": "password123"},
        )
        # 쿠키 확인
        assert "refresh_token" in register_response.cookies

        # Refresh Token으로 갱신 (쿠키가 자동으로 전송됨)
        # httpx AsyncClient는 자동으로 쿠키를 유지하므로 별도 설정 불필요
        response = await client.post("/api/v1/auth/refresh", json={})

        assert response.status_code == 200
        data = response.json()
        # 토큰은 httpOnly 쿠키에 저장되므로 응답 본문에 없음
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert data["token_type"] == "bearer"

        # 새로운 쿠키 확인
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """잘못된 Refresh Token 테스트"""
        # 잘못된 쿠키 설정
        client.cookies.set("refresh_token", "invalid_token")

        response = await client.post("/api/v1/auth/refresh", json={})

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_token_with_access_token(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Access Token으로 갱신 시도 (실패해야 함)"""
        # 회원가입으로 토큰 획득
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "wrongtype@example.com", "password": "password123"},
        )
        # access_token 쿠키를 refresh_token 쿠키 위치에 설정
        access_token = register_response.cookies.get("access_token")

        # Access Token으로 갱신 시도
        client.cookies.set("refresh_token", access_token)
        response = await client.post("/api/v1/auth/refresh", json={})

        assert response.status_code == 401
