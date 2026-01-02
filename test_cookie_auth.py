#!/usr/bin/env python3
"""
Cookie-Based Authentication API Test Script

This script tests all authentication flows to verify cookie-based JWT implementation.
Run this after starting the backend service.

Usage:
    python test_cookie_auth.py

Requirements:
    pip install requests
"""

import requests
import json
import sys
from typing import Dict, Optional, Tuple


class Colors:
    """ANSI color codes for terminal output"""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


class CookieAuthTester:
    """Test suite for cookie-based authentication"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []

    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}\n")

    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓ {text}{Colors.END}")

    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.RED}✗ {text}{Colors.END}")

    def print_info(self, text: str):
        """Print info message"""
        print(f"{Colors.YELLOW}ℹ {text}{Colors.END}")

    def verify_cookies(self, response: requests.Response, should_have_cookies: bool = True) -> bool:
        """Verify that cookies are set correctly"""
        cookies = response.cookies
        has_access = 'access_token' in cookies
        has_refresh = 'refresh_token' in cookies

        if should_have_cookies:
            if has_access and has_refresh:
                self.print_success("Cookies set: access_token and refresh_token")
                # Note: httpOnly cannot be verified from requests library
                # as it's a browser-only security feature
                self.print_info("Note: httpOnly flag should be verified in browser DevTools")
                return True
            else:
                self.print_error(f"Missing cookies. access_token: {has_access}, refresh_token: {has_refresh}")
                return False
        else:
            if not has_access and not has_refresh:
                self.print_success("Cookies cleared as expected")
                return True
            else:
                self.print_error(f"Cookies not cleared. access_token: {has_access}, refresh_token: {has_refresh}")
                return False

    def verify_no_tokens_in_body(self, data: Dict) -> bool:
        """Verify that tokens are NOT in response body"""
        has_access = 'access_token' in data
        has_refresh = 'refresh_token' in data

        if not has_access and not has_refresh:
            self.print_success("No tokens in response body (as expected)")
            return True
        else:
            self.print_error(f"Tokens found in response body! access_token: {has_access}, refresh_token: {has_refresh}")
            return False

    def test_1_login(self) -> bool:
        """Test 1: Login with cookies"""
        self.print_header("Test 1: Login Flow (POST /auth/login)")

        # Test credentials (adjust as needed)
        payload = {
            "email": "test@example.com",
            "password": "testpassword123"
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=payload
            )

            self.print_info(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                self.print_success("Login successful")

                # Verify response structure
                if 'user' in data:
                    self.print_success(f"User object returned: {data['user'].get('email')}")
                else:
                    self.print_error("No user object in response")
                    return False

                # Verify no tokens in body
                if not self.verify_no_tokens_in_body(data):
                    return False

                # Verify cookies are set
                if not self.verify_cookies(response, should_have_cookies=True):
                    return False

                self.print_success("Test 1 PASSED")
                return True

            elif response.status_code == 401:
                self.print_error("Login failed: Invalid credentials")
                self.print_info("Please create a test user first or update credentials in script")
                return False
            else:
                self.print_error(f"Unexpected status code: {response.status_code}")
                self.print_error(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            self.print_error(f"Request failed: {e}")
            return False

    def test_2_protected_api(self) -> bool:
        """Test 2: Access protected API with cookies"""
        self.print_header("Test 2: Protected API Call (GET /auth/me)")

        try:
            # Session should have cookies from login
            response = self.session.get(f"{self.base_url}/api/v1/auth/me")

            self.print_info(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                self.print_success("Protected API call successful")
                self.print_success(f"User authenticated: {data.get('email')}")

                # Verify cookies were sent (check via session cookies)
                if self.session.cookies:
                    self.print_success(f"Cookies sent with request: {len(self.session.cookies)} cookies")
                else:
                    self.print_error("No cookies sent with request")
                    return False

                self.print_success("Test 2 PASSED")
                return True
            else:
                self.print_error(f"Protected API call failed: {response.status_code}")
                self.print_error(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            self.print_error(f"Request failed: {e}")
            return False

    def test_3_token_refresh(self) -> bool:
        """Test 3: Token refresh with cookies"""
        self.print_header("Test 3: Token Refresh Flow (POST /auth/refresh)")

        try:
            # Call refresh endpoint (should use refresh_token from cookie)
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={}  # Empty body - refresh_token comes from cookie
            )

            self.print_info(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                self.print_success("Token refresh successful")

                # Verify no tokens in body
                if not self.verify_no_tokens_in_body(data):
                    return False

                # Verify new cookies are set
                if not self.verify_cookies(response, should_have_cookies=True):
                    return False

                self.print_success("Test 3 PASSED")
                return True
            else:
                self.print_error(f"Token refresh failed: {response.status_code}")
                self.print_error(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            self.print_error(f"Request failed: {e}")
            return False

    def test_4_logout(self) -> bool:
        """Test 4: Logout and clear cookies"""
        self.print_header("Test 4: Logout Flow (POST /auth/logout)")

        try:
            # Call logout endpoint
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/logout",
                json={}  # Empty body - tokens come from cookies
            )

            self.print_info(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                self.print_success("Logout successful")

                # Verify cookies are cleared (max_age=0)
                # In requests library, expired cookies are removed from session
                # Check that cookies are no longer in session
                has_access = 'access_token' in self.session.cookies
                has_refresh = 'refresh_token' in self.session.cookies

                if not has_access and not has_refresh:
                    self.print_success("Cookies cleared from session")
                else:
                    self.print_error(f"Cookies still in session. access: {has_access}, refresh: {has_refresh}")
                    return False

                self.print_success("Test 4 PASSED")
                return True
            else:
                self.print_error(f"Logout failed: {response.status_code}")
                self.print_error(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            self.print_error(f"Request failed: {e}")
            return False

    def test_5_register(self) -> bool:
        """Test 5: Registration with cookies"""
        self.print_header("Test 5: Registration Flow (POST /auth/register)")

        import time
        # Use timestamp to create unique email
        unique_email = f"testuser_{int(time.time())}@example.com"

        payload = {
            "email": unique_email,
            "password": "TestPassword123!",
            "name": "Test User"
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/register",
                json=payload
            )

            self.print_info(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                self.print_success("Registration successful")

                # Verify response structure
                if 'user' in data:
                    self.print_success(f"User created: {data['user'].get('email')}")
                else:
                    self.print_error("No user object in response")
                    return False

                # Verify no tokens in body
                if not self.verify_no_tokens_in_body(data):
                    return False

                # Verify cookies are set
                if not self.verify_cookies(response, should_have_cookies=True):
                    return False

                self.print_success("Test 5 PASSED")
                return True

            elif response.status_code == 400:
                self.print_error(f"Registration failed: {response.json()}")
                return False
            else:
                self.print_error(f"Unexpected status code: {response.status_code}")
                self.print_error(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            self.print_error(f"Request failed: {e}")
            return False

    def test_6_unauthorized_access(self) -> bool:
        """Test 6: Access protected resource without cookies"""
        self.print_header("Test 6: Unauthorized Access (No Cookies)")

        # Create new session without cookies
        new_session = requests.Session()

        try:
            response = new_session.get(f"{self.base_url}/api/v1/auth/me")

            self.print_info(f"Status Code: {response.status_code}")

            if response.status_code == 401:
                self.print_success("Unauthorized access correctly rejected")
                self.print_success("Test 6 PASSED")
                return True
            else:
                self.print_error(f"Expected 401, got {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            self.print_error(f"Request failed: {e}")
            return False

    def run_all_tests(self):
        """Run all test cases"""
        self.print_header("🚀 Cookie-Based Authentication Test Suite")

        # Test if backend is running
        try:
            response = requests.get(f"{self.base_url}/health")
            self.print_success(f"Backend is running at {self.base_url}")
        except requests.exceptions.RequestException:
            self.print_error(f"Backend is not running at {self.base_url}")
            self.print_info("Please start the backend with: make dev")
            sys.exit(1)

        # Run tests
        tests = [
            ("Test 1: Login", self.test_1_login),
            ("Test 2: Protected API", self.test_2_protected_api),
            ("Test 3: Token Refresh", self.test_3_token_refresh),
            ("Test 4: Logout", self.test_4_logout),
            ("Test 5: Registration", self.test_5_register),
            ("Test 6: Unauthorized Access", self.test_6_unauthorized_access),
        ]

        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                self.print_error(f"Test crashed: {e}")
                results.append((test_name, False))

        # Print summary
        self.print_header("📊 Test Summary")
        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = f"{Colors.GREEN}PASSED{Colors.END}" if result else f"{Colors.RED}FAILED{Colors.END}"
            print(f"{test_name}: {status}")

        print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.END}")

        if passed == total:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All tests passed!{Colors.END}")
            print(f"{Colors.GREEN}Cookie-based authentication is working correctly.{Colors.END}")
            return 0
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ Some tests failed.{Colors.END}")
            print(f"{Colors.YELLOW}Please check the errors above and fix the issues.{Colors.END}")
            return 1


if __name__ == "__main__":
    print(f"{Colors.BLUE}{Colors.BOLD}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║     Cookie-Based JWT Authentication Test Suite                    ║")
    print("║     Testing httpOnly cookie implementation for XSS protection     ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    tester = CookieAuthTester()
    exit_code = tester.run_all_tests()

    print(f"\n{Colors.BLUE}Note: This script tests API-level cookie handling.{Colors.END}")
    print(f"{Colors.BLUE}For complete verification, also test in browser DevTools:{Colors.END}")
    print(f"{Colors.YELLOW}  - Verify httpOnly flag in Application/Storage tab{Colors.END}")
    print(f"{Colors.YELLOW}  - Verify cookies cannot be accessed via document.cookie{Colors.END}")
    print(f"{Colors.YELLOW}  - Verify frontend axios withCredentials: true{Colors.END}")
    print(f"{Colors.YELLOW}  - See COOKIE_AUTH_TESTING_GUIDE.md for complete manual tests{Colors.END}\n")

    sys.exit(exit_code)
