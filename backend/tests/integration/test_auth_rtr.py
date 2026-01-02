"""
RTR (Refresh Token Rotation) Integration Tests
Redis 연동 및 RTR 로직(토큰 교체, 재사용 감지, 로그아웃) 검증
"""

import pytest
from jose import jwt
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from aiocache import caches

from backend.features.auth.repository import UserRepository
from backend.core.config import settings

@pytest.mark.asyncio
async def test_rtr_flow_complete(client: AsyncClient, db_session: AsyncSession):
    """
    RTR 전체 플로우 테스트 (Cookie 기반)
    1. 회원가입 -> 토큰 발급 (httpOnly 쿠키 & Redis 저장 확인)
    2. 토큰 갱신 -> Old 토큰 삭제 & New 토큰 저장 확인
    3. Old 토큰 재사용 시도 -> 실패 확인
    4. 로그아웃 -> 토큰 삭제 확인
    """
    import uuid
    email = f"rtr_test_{uuid.uuid4()}@example.com"
    password = "password123"

    # 1. 회원가입 (토큰이 httpOnly 쿠키로 설정됨)
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password}
    )
    assert response.status_code == 201
    data = response.json()
    # 토큰은 응답 본문이 아닌 쿠키에 있음
    assert "access_token" not in data
    assert "refresh_token" not in data

    # 쿠키에서 토큰 추출
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies
    access_token = response.cookies.get("access_token")
    refresh_token = response.cookies.get("refresh_token")

    # JTI 추출
    payload = jwt.decode(refresh_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    jti = payload.get("jti")
    assert jti is not None
    user_id = payload.get("sub")

    # Redis 확인
    cache = caches.get("default")
    cached_user_id = await cache.get(f"refresh_token:{jti}")
    print(f"DEBUG: JTI={jti}, UserID={user_id}, Cached={cached_user_id}")
    assert cached_user_id == user_id

    # 2. 토큰 갱신 (RTR) - 쿠키가 자동으로 전송됨
    import asyncio
    await asyncio.sleep(2)  # Ensure exp changes (JWT exp is in seconds)
    response = await client.post("/api/v1/auth/refresh", json={})
    assert response.status_code == 200
    new_data = response.json()
    # 새 토큰도 응답 본문이 아닌 쿠키에 있음
    assert "access_token" not in new_data
    assert "refresh_token" not in new_data

    # 새 쿠키에서 토큰 추출
    new_access_token = response.cookies.get("access_token")
    new_refresh_token = response.cookies.get("refresh_token")

    assert new_access_token != access_token
    assert new_refresh_token != refresh_token

    # New JTI 추출
    new_payload = jwt.decode(new_refresh_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    new_jti = new_payload.get("jti")
    assert new_jti is not None
    assert new_jti != jti

    # Redis 확인: Old Token은 삭제되어야 함
    old_cached = await cache.get(f"refresh_token:{jti}")
    print(f"DEBUG: Old JTI={jti}, Old Cached={old_cached}")
    assert old_cached is None

    # Redis 확인: New Token은 저장되어야 함
    new_cached = await cache.get(f"refresh_token:{new_jti}")
    print(f"DEBUG: New JTI={new_jti}, New Cached={new_cached}")
    assert new_cached == user_id

    # 3. Old Token 재사용 시도 -> 실패 (401)
    # 수동으로 old refresh_token 쿠키 설정
    client.cookies.set("refresh_token", refresh_token)
    response = await client.post("/api/v1/auth/refresh", json={})
    assert response.status_code == 401

    # 4. 로그아웃 (쿠키가 자동으로 전송됨)
    # 다시 new refresh_token 쿠키 설정
    client.cookies.set("refresh_token", new_refresh_token)
    client.cookies.set("access_token", new_access_token)
    response = await client.post("/api/v1/auth/logout", json={})
    assert response.status_code == 204

    # Redis 확인: New Token 삭제되어야 함
    logout_cached = await cache.get(f"refresh_token:{new_jti}")
    assert logout_cached is None

