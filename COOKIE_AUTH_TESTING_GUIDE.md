# Cookie-Based Authentication Testing Guide

## Overview
This guide provides comprehensive manual testing procedures for the cookie-based JWT authentication system. All tests should be performed to verify that httpOnly cookies are working correctly for XSS protection.

---

## Prerequisites

### 1. Start the Services
```bash
# Start backend and database
make dev

# In a separate terminal, start frontend
cd frontend
npm run dev
```

### 2. Testing Tools
- Browser DevTools (Chrome/Firefox recommended)
- Network tab for monitoring requests/responses
- Application/Storage tab for viewing cookies
- Optional: Postman or curl for API testing

---

## Test Suite

### Test 1: Login Flow (POST /auth/login)

#### Objective
Verify that login sets httpOnly cookies and returns user info without tokens in response body.

#### Steps
1. Open browser DevTools → Application/Storage → Cookies
2. Navigate to frontend login page (typically `http://localhost:5173/login`)
3. Enter valid credentials and submit login form
4. **Verify Response (Network Tab)**:
   - Status: `200 OK`
   - Response body contains:
     - `user` object with `id`, `email`, `name`, etc.
     - `token_type: "bearer"`
   - Response body **DOES NOT** contain:
     - `access_token` field
     - `refresh_token` field

5. **Verify Cookies (Application Tab)**:
   - `access_token` cookie exists with:
     - HttpOnly: ✓ (checked)
     - Secure: ✓ or ✗ (depending on COOKIE_SECURE setting)
     - SameSite: `Lax` or `Strict`
     - Path: `/`
     - Max-Age: ~900 seconds (15 minutes)
   - `refresh_token` cookie exists with:
     - HttpOnly: ✓ (checked)
     - Secure: ✓ or ✗ (depending on COOKIE_SECURE setting)
     - SameSite: `Lax` or `Strict`
     - Path: `/`
     - Max-Age: ~604800 seconds (7 days)

6. **Verify localStorage**:
   - Check that `access_token` is **NOT** stored in localStorage
   - Check that `refresh_token` is **NOT** stored in localStorage
   - Verify that `user` object is stored in localStorage (for UI display)

#### Expected Result
✅ Login successful with cookies set
✅ No tokens in response body
✅ httpOnly cookies cannot be accessed via JavaScript
✅ User info available for UI rendering

---

### Test 2: Protected API Calls (with Cookie Authentication)

#### Objective
Verify that authenticated API requests automatically send cookies and work without Authorization header.

#### Steps
1. After successful login (Test 1), navigate to a page that makes protected API calls
2. Open Network tab and monitor API requests
3. Trigger a protected endpoint (e.g., GET /storybooks, GET /auth/me)
4. **Verify Request Headers**:
   - `Cookie` header is present with `access_token=...` and `refresh_token=...`
   - **NO** `Authorization` header (or if present, it should be ignored)

5. **Verify Response**:
   - Status: `200 OK`
   - Protected resource data returned successfully

6. **Verify in Console**:
   ```javascript
   // Try to access cookies from JavaScript console
   document.cookie
   ```
   - Should **NOT** show `access_token` or `refresh_token` (httpOnly protection)

#### Expected Result
✅ Cookies sent automatically with requests
✅ Protected endpoints respond successfully
✅ Tokens inaccessible via JavaScript console

---

### Test 3: Token Refresh Flow (POST /auth/refresh)

#### Objective
Verify that token refresh works with cookies and sets new cookies on success.

#### Steps

**Method 1: Natural Expiry (Wait for Access Token to Expire)**
1. Login successfully
2. Wait 15+ minutes for access_token to expire
3. Make a protected API call
4. Monitor Network tab for:
   - Initial request returns `401 Unauthorized`
   - Automatic retry to `/auth/refresh`
   - New cookies set in response
   - Original request retried successfully

**Method 2: Simulated Expiry (Modify Cookie)**
1. Login successfully
2. Open DevTools → Application → Cookies
3. Delete the `access_token` cookie (keep `refresh_token`)
4. Trigger a protected API call
5. Monitor Network tab

**What to Verify:**
- `/auth/refresh` request:
  - Method: `POST`
  - Body: `{}` (empty - refresh_token sent as cookie)
  - Cookie header contains `refresh_token`
- `/auth/refresh` response:
  - Status: `200 OK`
  - Response body: `{"token_type": "bearer", "message": "..."}`
  - **NO** `access_token` or `refresh_token` in response body
  - Set-Cookie headers for new `access_token` and `refresh_token`

- **Verify New Cookies**:
  - New `access_token` cookie set with fresh Max-Age
  - New `refresh_token` cookie set with fresh Max-Age
  - Both httpOnly, secure, sameSite attributes preserved

#### Expected Result
✅ Refresh endpoint called automatically on 401
✅ No tokens in request body
✅ New cookies set in response
✅ Subsequent requests succeed with new tokens

---

### Test 4: Logout Flow (POST /auth/logout)

#### Objective
Verify that logout clears cookies and invalidates session.

#### Steps
1. Login successfully (ensure cookies are set)
2. Trigger logout action (click logout button)
3. **Verify Request (Network Tab)**:
   - Method: `POST /auth/logout`
   - Request body: `{}` (empty - tokens sent as cookies)
   - Cookie header contains both `access_token` and `refresh_token`

4. **Verify Response**:
   - Status: `200 OK`
   - Set-Cookie headers to clear cookies:
     - `access_token=; Max-Age=0`
     - `refresh_token=; Max-Age=0`

5. **Verify Cookies (Application Tab)**:
   - `access_token` cookie removed or expired
   - `refresh_token` cookie removed or expired

6. **Verify localStorage**:
   - `user` object removed from localStorage

7. **Verify Session Invalidation**:
   - Try to access a protected page
   - Should redirect to login page
   - Protected API calls should return `401 Unauthorized`

#### Expected Result
✅ Logout successful
✅ Cookies cleared (Max-Age=0)
✅ User info cleared from localStorage
✅ Protected pages redirect to login

---

### Test 5: Registration Flow (POST /auth/register)

#### Objective
Verify that user registration sets cookies like login.

#### Steps
1. Clear all cookies and localStorage
2. Navigate to registration page
3. Fill in registration form with new user details
4. Submit registration
5. **Verify Response**:
   - Status: `200 OK`
   - Response body contains user object
   - Response body **DOES NOT** contain tokens

6. **Verify Cookies**:
   - Same verification as Test 1 (Login Flow)
   - Both `access_token` and `refresh_token` cookies set
   - All security attributes correct (httpOnly, secure, sameSite)

#### Expected Result
✅ Registration successful
✅ Cookies set automatically
✅ No tokens in response body
✅ User automatically logged in after registration

---

### Test 6: Google OAuth Flow (POST /auth/google)

#### Objective
Verify that Google OAuth login works with cookie-based authentication.

#### Steps
1. Clear all cookies and localStorage
2. Navigate to login page
3. Click "Sign in with Google" button
4. Complete Google OAuth flow
5. **Verify Callback/Redirect**:
   - After OAuth callback, user redirected to app
   - Check Network tab for `/auth/google` request

6. **Verify Response**:
   - Status: `200 OK`
   - Response body contains user object
   - Response body **DOES NOT** contain tokens

7. **Verify Cookies**:
   - Same verification as Test 1 (Login Flow)
   - Both cookies set with proper attributes

8. **Verify Session**:
   - User successfully authenticated
   - Protected pages accessible
   - User info displayed in UI

#### Expected Result
✅ Google OAuth successful
✅ Cookies set via OAuth flow
✅ No tokens in response body
✅ User authenticated and can access protected resources

---

## Test 7: Auth Status Check on Mount (GET /auth/me)

#### Objective
Verify that auth status is validated on page load/refresh.

#### Steps
1. Login successfully
2. Refresh the page (F5 or Cmd+R)
3. **Verify Network Tab**:
   - Request to `GET /auth/me` made on mount
   - Cookie header contains `access_token`
   - **NO** Authorization header

4. **Verify Response**:
   - Status: `200 OK`
   - User object returned
   - User state restored in UI

5. **Test Invalid Cookie**:
   - Manually edit/corrupt the `access_token` cookie value
   - Refresh page
   - Verify:
     - `/auth/me` returns `401 Unauthorized`
     - User logged out
     - Redirected to login page

#### Expected Result
✅ Auth validated on page load
✅ Valid cookies restore user session
✅ Invalid cookies trigger logout

---

## Test 8: CORS and Cookie Handling

#### Objective
Verify that CORS is configured correctly for cookie-based auth.

#### Steps
1. Check axios client configuration:
   ```javascript
   // frontend/src/api/client.ts should have:
   withCredentials: true
   ```

2. Verify backend CORS settings allow credentials:
   ```python
   # backend should have:
   allow_credentials=True
   ```

3. **Test Cross-Origin Requests**:
   - Make API calls from frontend to backend
   - Verify cookies are sent with every request
   - Check that CORS headers are present in responses

#### Expected Result
✅ `withCredentials: true` in axios config
✅ Cookies sent with cross-origin requests
✅ No CORS errors in console

---

## Test 9: Security Verification

#### Objective
Verify XSS protection and cookie security attributes.

#### Steps
1. **HttpOnly Test (XSS Protection)**:
   - Open browser console
   - Try to access cookies:
     ```javascript
     document.cookie
     ```
   - Verify `access_token` and `refresh_token` are **NOT visible**
   - Try to modify cookies - should fail

2. **Secure Flag Test** (if COOKIE_SECURE=true):
   - Verify cookies only sent over HTTPS
   - HTTP requests should not send cookies

3. **SameSite Test** (CSRF Protection):
   - Verify SameSite attribute is `Lax` or `Strict`
   - Prevents CSRF attacks

#### Expected Result
✅ Cookies not accessible via JavaScript
✅ httpOnly flag prevents XSS token theft
✅ Secure and SameSite flags provide additional protection

---

## Test 10: Migration Test (Existing Users)

#### Objective
Verify that users with old localStorage tokens are handled gracefully.

#### Steps
1. Manually add old tokens to localStorage:
   ```javascript
   localStorage.setItem('access_token', 'old-token-value')
   localStorage.setItem('refresh_token', 'old-refresh-token')
   ```

2. Refresh page
3. **Verify Behavior**:
   - Old tokens ignored
   - `/auth/me` called with cookies (not old tokens)
   - User logged out if no valid cookies
   - Prompted to login again

4. **After Fresh Login**:
   - Old localStorage tokens remain (but ignored)
   - New httpOnly cookies take precedence
   - App functions normally with cookies

#### Expected Result
✅ Old localStorage tokens ignored
✅ Cookie-based auth takes precedence
✅ Users can login fresh with new system

---

## Troubleshooting

### Issue: Cookies Not Being Set

**Possible Causes:**
- CORS not configured with `credentials: true`
- Frontend axios missing `withCredentials: true`
- Backend not sending Set-Cookie headers

**Check:**
```bash
# Check backend logs for cookie setting
make dev-logs-backend | grep "SET COOKIES"

# Verify response headers contain Set-Cookie
# Look for: Set-Cookie: access_token=...; HttpOnly; ...
```

### Issue: Cookies Not Being Sent

**Possible Causes:**
- axios client missing `withCredentials: true`
- CORS origin mismatch
- Cookie domain mismatch

**Check:**
```javascript
// Verify in frontend/src/api/client.ts
const client = axios.create({
  withCredentials: true, // This MUST be present
});
```

### Issue: 401 Errors on Every Request

**Possible Causes:**
- Cookies cleared/expired
- Backend not reading cookies correctly
- Cookie path/domain mismatch

**Check:**
```bash
# Check backend logs for token extraction
make dev-logs-backend | grep "Token source"

# Should see: "Token source: cookie" or "Token source: header"
```

---

## Success Criteria

All tests must pass:
- ✅ Test 1: Login sets cookies, no tokens in response
- ✅ Test 2: Protected APIs work with cookies
- ✅ Test 3: Token refresh works with cookies
- ✅ Test 4: Logout clears cookies
- ✅ Test 5: Registration sets cookies
- ✅ Test 6: Google OAuth sets cookies
- ✅ Test 7: Auth validated on mount
- ✅ Test 8: CORS configured for credentials
- ✅ Test 9: httpOnly prevents JS access
- ✅ Test 10: Migration handled gracefully

---

## Testing Checklist

- [ ] Backend is running (`make dev`)
- [ ] Frontend is running (`cd frontend && npm run dev`)
- [ ] Browser DevTools open
- [ ] Network tab monitoring enabled
- [ ] Cookies/Application tab visible
- [ ] Test 1: Login ✓
- [ ] Test 2: Protected API calls ✓
- [ ] Test 3: Token refresh ✓
- [ ] Test 4: Logout ✓
- [ ] Test 5: Registration ✓
- [ ] Test 6: Google OAuth ✓
- [ ] Test 7: Auth on mount ✓
- [ ] Test 8: CORS ✓
- [ ] Test 9: Security ✓
- [ ] Test 10: Migration ✓
- [ ] No console errors
- [ ] No network errors
- [ ] Tokens NOT in localStorage
- [ ] Cookies httpOnly ✓

---

## Notes

- All tests should be performed in a fresh browser session
- Clear cookies and localStorage between tests for isolation
- Test in multiple browsers (Chrome, Firefox, Safari)
- Test with DevTools security tab to verify httpOnly
- Document any failures with screenshots and network logs

---

## Backend Logging

Look for these log messages to confirm cookie operations:

```
🍪 [SET COOKIES] Auth cookies set successfully
🍪 [CLEAR COOKIES] Auth cookies cleared successfully
🔑 [AUTH] Token source: cookie
✅ [AUTH] User authenticated successfully via cookie
```

These logs confirm that the cookie-based authentication system is working correctly.
