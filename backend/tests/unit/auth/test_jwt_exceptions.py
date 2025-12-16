"""
JWT Manager Exception Tests
JWT Manager 예외 처리 테스트
"""

import pytest
from unittest.mock import patch
from jose import ExpiredSignatureError, JWTError

from backend.core.auth.jwt_manager import JWTManager
from backend.core.auth.exceptions import TokenExpiredException, InvalidTokenException

def test_decode_token_expired():
    """만료된 토큰 디코딩 시 TokenExpiredException 발생 확인"""
    with patch("jose.jwt.decode", side_effect=ExpiredSignatureError):
        with pytest.raises(TokenExpiredException):
            JWTManager.decode_token("expired_token")

def test_decode_token_invalid():
    """유효하지 않은 토큰 디코딩 시 InvalidTokenException 발생 확인"""
    with patch("jose.jwt.decode", side_effect=JWTError):
        with pytest.raises(InvalidTokenException):
            JWTManager.decode_token("invalid_token")

def test_verify_token_invalid_type():
    """토큰 타입 불일치 시 InvalidTokenException 발생 확인"""
    # Mocking decode_token to return a valid payload
    with patch.object(JWTManager, "decode_token", return_value={"type": "access"}):
        # type="refresh" 로 검증 시도 -> type mismatch
        with pytest.raises(InvalidTokenException):
            JWTManager.verify_token("valid_access_token", token_type="refresh")
