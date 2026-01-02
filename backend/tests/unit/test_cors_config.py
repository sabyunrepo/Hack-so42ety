"""
CORS Configuration Unit Tests
CORS 헤더 설정 파싱 및 적용 테스트
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI

from backend.core.middleware.cors import setup_cors
from backend.core.config import Settings


class TestCORSConfiguration:
    """CORS 설정 단위 테스트"""

    def test_default_allowed_headers_list(self):
        """기본 허용 헤더 리스트 테스트"""
        settings = Settings()

        assert settings.cors_allow_headers is not None
        assert isinstance(settings.cors_allow_headers, str)

        # Default should be explicit list, not wildcard
        assert settings.cors_allow_headers != "*"

        # Check default headers are present
        default_headers = "Content-Type,Authorization,Accept,X-Request-ID"
        assert settings.cors_allow_headers == default_headers

    def test_comma_separated_parsing(self):
        """쉼표로 구분된 헤더 파싱 테스트"""
        # Test header parsing logic
        test_header_string = "Content-Type,Authorization,Accept,X-Request-ID"

        # Simulate the parsing logic from setup_cors
        parsed_headers = (
            test_header_string.split(",")
            if test_header_string != "*"
            else ["*"]
        )

        assert isinstance(parsed_headers, list)
        assert len(parsed_headers) == 4
        assert "Content-Type" in parsed_headers
        assert "Authorization" in parsed_headers
        assert "Accept" in parsed_headers
        assert "X-Request-ID" in parsed_headers

    def test_wildcard_handling(self):
        """와일드카드(*) 처리 테스트 - 하위 호환성"""
        # Test wildcard special case
        wildcard_string = "*"

        # Simulate the parsing logic from setup_cors
        parsed_headers = (
            wildcard_string.split(",")
            if wildcard_string != "*"
            else ["*"]
        )

        assert isinstance(parsed_headers, list)
        assert len(parsed_headers) == 1
        assert parsed_headers[0] == "*"

    def test_custom_header_list_parsing(self):
        """커스텀 헤더 리스트 파싱 테스트"""
        custom_headers = "Content-Type,Authorization,X-Custom-Header,X-API-Key"

        # Simulate the parsing logic from setup_cors
        parsed_headers = (
            custom_headers.split(",")
            if custom_headers != "*"
            else ["*"]
        )

        assert isinstance(parsed_headers, list)
        assert len(parsed_headers) == 4
        assert "Content-Type" in parsed_headers
        assert "Authorization" in parsed_headers
        assert "X-Custom-Header" in parsed_headers
        assert "X-API-Key" in parsed_headers

    def test_single_header_parsing(self):
        """단일 헤더 파싱 테스트"""
        single_header = "Content-Type"

        # Simulate the parsing logic from setup_cors
        parsed_headers = (
            single_header.split(",")
            if single_header != "*"
            else ["*"]
        )

        assert isinstance(parsed_headers, list)
        assert len(parsed_headers) == 1
        assert parsed_headers[0] == "Content-Type"

    @patch('backend.core.middleware.cors.settings')
    def test_setup_cors_with_default_headers(self, mock_settings):
        """기본 헤더로 CORS 미들웨어 설정 테스트"""
        # Mock settings
        mock_settings.cors_origins = ["http://localhost:5173"]
        mock_settings.cors_allow_credentials = True
        mock_settings.cors_allow_methods = "GET,POST,PUT,DELETE,OPTIONS"
        mock_settings.cors_allow_headers = "Content-Type,Authorization,Accept,X-Request-ID"

        # Create a mock FastAPI app
        app = FastAPI()

        # Call setup_cors
        setup_cors(app)

        # Verify middleware was added
        assert len(app.user_middleware) > 0

        # Get the CORS middleware
        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break

        assert cors_middleware is not None

        # Verify allow_headers was parsed correctly
        expected_headers = ["Content-Type", "Authorization", "Accept", "X-Request-ID"]
        assert cors_middleware.kwargs["allow_headers"] == expected_headers

    @patch('backend.core.middleware.cors.settings')
    def test_setup_cors_with_wildcard(self, mock_settings):
        """와일드카드(*) 설정으로 CORS 미들웨어 테스트"""
        # Mock settings with wildcard
        mock_settings.cors_origins = ["http://localhost:5173"]
        mock_settings.cors_allow_credentials = True
        mock_settings.cors_allow_methods = "GET,POST,PUT,DELETE,OPTIONS"
        mock_settings.cors_allow_headers = "*"

        # Create a mock FastAPI app
        app = FastAPI()

        # Call setup_cors
        setup_cors(app)

        # Verify middleware was added
        assert len(app.user_middleware) > 0

        # Get the CORS middleware
        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break

        assert cors_middleware is not None

        # Verify allow_headers is wildcard
        assert cors_middleware.kwargs["allow_headers"] == ["*"]

    @patch('backend.core.middleware.cors.settings')
    def test_setup_cors_with_custom_headers(self, mock_settings):
        """커스텀 헤더 리스트로 CORS 미들웨어 설정 테스트"""
        # Mock settings with custom headers
        mock_settings.cors_origins = ["http://localhost:5173"]
        mock_settings.cors_allow_credentials = True
        mock_settings.cors_allow_methods = "GET,POST,PUT,DELETE,OPTIONS"
        mock_settings.cors_allow_headers = "Content-Type,Authorization,X-Custom-Header"

        # Create a mock FastAPI app
        app = FastAPI()

        # Call setup_cors
        setup_cors(app)

        # Verify middleware was added
        assert len(app.user_middleware) > 0

        # Get the CORS middleware
        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break

        assert cors_middleware is not None

        # Verify custom headers were parsed correctly
        expected_headers = ["Content-Type", "Authorization", "X-Custom-Header"]
        assert cors_middleware.kwargs["allow_headers"] == expected_headers

    @patch('backend.core.middleware.cors.settings')
    def test_setup_cors_expose_headers(self, mock_settings):
        """expose_headers 설정 테스트"""
        # Mock settings
        mock_settings.cors_origins = ["http://localhost:5173"]
        mock_settings.cors_allow_credentials = True
        mock_settings.cors_allow_methods = "GET,POST,PUT,DELETE,OPTIONS"
        mock_settings.cors_allow_headers = "Content-Type,Authorization"

        # Create a mock FastAPI app
        app = FastAPI()

        # Call setup_cors
        setup_cors(app)

        # Get the CORS middleware
        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break

        assert cors_middleware is not None

        # Verify expose_headers includes Content-Disposition for file downloads
        assert "expose_headers" in cors_middleware.kwargs
        assert "Content-Disposition" in cors_middleware.kwargs["expose_headers"]

    @patch('backend.core.middleware.cors.settings')
    def test_setup_cors_methods_parsing(self, mock_settings):
        """CORS methods 파싱 테스트"""
        # Mock settings
        mock_settings.cors_origins = ["http://localhost:5173"]
        mock_settings.cors_allow_credentials = True
        mock_settings.cors_allow_methods = "GET,POST,PUT,DELETE,OPTIONS"
        mock_settings.cors_allow_headers = "Content-Type,Authorization"

        # Create a mock FastAPI app
        app = FastAPI()

        # Call setup_cors
        setup_cors(app)

        # Get the CORS middleware
        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break

        assert cors_middleware is not None

        # Verify methods were parsed correctly
        expected_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        assert cors_middleware.kwargs["allow_methods"] == expected_methods

    def test_empty_header_string_parsing(self):
        """빈 헤더 문자열 파싱 테스트"""
        empty_string = ""

        # Simulate the parsing logic from setup_cors
        parsed_headers = (
            empty_string.split(",")
            if empty_string != "*"
            else ["*"]
        )

        # Empty string split by comma returns list with one empty string
        assert isinstance(parsed_headers, list)
        assert len(parsed_headers) == 1
        assert parsed_headers[0] == ""

    def test_headers_with_spaces_parsing(self):
        """공백이 포함된 헤더 파싱 테스트"""
        headers_with_spaces = "Content-Type, Authorization, Accept"

        # Simulate the parsing logic from setup_cors
        parsed_headers = (
            headers_with_spaces.split(",")
            if headers_with_spaces != "*"
            else ["*"]
        )

        assert isinstance(parsed_headers, list)
        assert len(parsed_headers) == 3
        # Note: spaces are preserved in current implementation
        assert "Content-Type" in parsed_headers
        assert " Authorization" in parsed_headers
        assert " Accept" in parsed_headers
