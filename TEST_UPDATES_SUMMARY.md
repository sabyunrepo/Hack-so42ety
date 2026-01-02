# Test Updates for Cookie-Based Authentication

## Summary
Updated all existing auth-related integration and E2E tests to work with httpOnly cookie-based authentication instead of localStorage-based token management.

## Changes Made

### 1. Integration Tests - Auth Flow (`backend/tests/integration/test_auth_flow.py`)

**Updated Test Classes:**
- `TestAuthRegistrationFlow`
  - `test_register_new_user`: Now checks for tokens in cookies instead of response body

- `TestAuthLoginFlow`
  - `test_login_success`: Verifies tokens are in cookies, not response body

- `TestAuthGoogleOAuthFlow`
  - `test_google_oauth_new_user`: Checks cookies for tokens

- `TestAuthRefreshTokenFlow`
  - `test_refresh_token_success`: Uses empty request body, cookies sent automatically
  - `test_refresh_token_invalid`: Sets invalid cookie manually for testing
  - `test_refresh_token_with_access_token`: Sets access_token as refresh_token cookie to test failure

**Key Changes:**
- Added assertions to verify tokens are NOT in response body
- Added assertions to verify tokens ARE in response cookies
- Updated refresh endpoint calls to use empty request body `json={}`
- Removed token extraction from response JSON
- Rely on httpx AsyncClient's automatic cookie management

### 2. Integration Tests - RTR (`backend/tests/integration/test_auth_rtr.py`)

**Updated Test:**
- `test_rtr_flow_complete`: Complete RTR flow with cookie-based auth

**Key Changes:**
- Extract tokens from `response.cookies` instead of `response.json()`
- Verify tokens are NOT in response body
- Use empty request body for refresh endpoint
- Manually set cookies for testing old token reuse scenario
- Manually set cookies for logout endpoint testing

### 3. E2E Tests - Book Creation (`backend/tests/e2e/test_book_creation_flow.py`)

**Updated Test:**
- `test_book_creation_flow`: End-to-end book creation flow

**Key Changes:**
- Removed token extraction from login response JSON
- Removed `headers` parameter from all API calls
- Added cookie verification after login
- Rely on httpx AsyncClient's automatic cookie management for authenticated requests

### 4. Integration Tests - File Access (`backend/tests/integration/test_file_access.py`)

**Updated Tests:**
- `test_private_book_file_access_with_owner`
- `test_private_book_file_access_with_other_user`

**Key Changes:**
- Removed token extraction from login response JSON
- Removed `headers` parameter from file access API calls
- Added cookie verification after login
- Cookies are automatically sent with subsequent requests

### 5. Integration Tests - File Caching (`backend/tests/integration/test_file_caching.py`)

**Updated Test:**
- `test_private_file_no_caching`

**Key Changes:**
- Removed token extraction from login response JSON
- Removed `headers` parameter from file access API calls
- Added cookie verification after login

## Unit Tests

**No Changes Required:**
- `backend/tests/unit/auth/test_jwt_manager.py` - Tests JWT token creation/validation directly
- `backend/tests/unit/auth/test_google_oauth.py` - Tests Google OAuth provider
- `backend/tests/unit/auth/test_jwt_exceptions.py` - Tests JWT exceptions
- `backend/tests/unit/auth/test_credentials_provider.py` - Tests credentials provider

These unit tests test the underlying JWT functionality, not the HTTP layer, so they don't need updates.

## Testing Pattern

**Before (localStorage-based):**
```python
response = await client.post("/api/v1/auth/login", json={"email": "...", "password": "..."})
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
response = await client.get("/api/v1/protected", headers=headers)
```

**After (cookie-based):**
```python
response = await client.post("/api/v1/auth/login", json={"email": "...", "password": "..."})
assert "access_token" in response.cookies  # Verify cookie set
# httpx AsyncClient automatically maintains cookies
response = await client.get("/api/v1/protected")  # No headers needed
```

## Backwards Compatibility

The backend authentication dependencies (`get_current_user`, `get_optional_user_object`) support BOTH:
1. **Cookie-based auth (primary)**: Tokens from httpOnly cookies
2. **Header-based auth (fallback)**: Authorization header with Bearer token

However, auth endpoints (login, register, google, refresh) NO LONGER return tokens in response body - only in cookies. This means old clients expecting tokens in JSON will break, but authenticated API calls using Authorization headers will continue to work if tokens are obtained from another source.

## Test Execution

All tests should pass with the updated cookie-based authentication implementation. Run tests with:

```bash
# All tests
pytest backend/tests/

# Integration tests only
pytest backend/tests/integration/

# E2E tests only
pytest backend/tests/e2e/

# Specific test file
pytest backend/tests/integration/test_auth_flow.py
```

## Notes

- httpx `AsyncClient` automatically maintains cookies between requests in the same test
- Manual cookie setting is only needed for specific test scenarios (e.g., testing with invalid tokens)
- All tests follow the pattern of verifying cookies are set and NOT in response body
