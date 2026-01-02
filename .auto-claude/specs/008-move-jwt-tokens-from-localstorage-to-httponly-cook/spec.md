# Move JWT tokens from localStorage to httpOnly cookies

## Overview

JWT access and refresh tokens are stored in browser localStorage (frontend/src/components/AuthProvider.tsx, frontend/src/api/client.ts). localStorage is accessible via JavaScript, making tokens vulnerable to XSS attacks. If an attacker can inject malicious JavaScript, they can steal all user tokens.

## Rationale

XSS vulnerabilities are common in web applications. Storing authentication tokens in localStorage means any XSS vulnerability allows complete account takeover. httpOnly cookies cannot be accessed by JavaScript, providing defense in depth.

---
*This spec was created from ideation and is pending detailed specification.*
