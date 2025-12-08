# MoriAI Storybook API 명세서

**Base URL**: `http://localhost:8000/api/v1` (개발 환경)  
**Base URL**: `http://localhost/api/v1` (Nginx 프록시 사용 시)

**API 버전**: v1.1
**문서 업데이트**: 2025-12-02

---

## 목차
1. [인증 (Authentication)](#1-인증-authentication)
2. [동화책 (Storybook)](#2-동화책-storybook)
3. [TTS (Text-to-Speech)](#3-tts-text-to-speech)
4. [사용자 (User)](#4-사용자-user)
5. [공통 응답 형식](#5-공통-응답-형식)
6. [에러 코드](#6-에러-코드)

---

## 1. 인증 (Authentication)

### 1.1. 회원가입

**Endpoint**: `POST /api/v1/auth/register`

**설명**: 이메일과 비밀번호로 새로운 계정을 생성합니다.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securePassword123!"
}
```

**Request Schema**:
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| email | string | ✅ | 사용자 이메일 (유효한 이메일 형식) |
| password | string | ✅ | 비밀번호 (최소 8자) |

**Response** (201 Created):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "oauth_provider": null,
    "is_active": true,
    "created_at": "2025-11-30T12:00:00Z"
  }
}
```

**Error Responses**:
- `400 Bad Request`: 이메일 중복 또는 유효성 검증 실패
  ```json
  {
    "detail": "Email already registered"
  }
  ```

---

### 1.2. 로그인

**Endpoint**: `POST /api/v1/auth/login`

**설명**: 이메일과 비밀번호로 로그인합니다.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securePassword123!"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "oauth_provider": null,
    "is_active": true,
    "created_at": "2025-11-30T12:00:00Z"
  }
}
```

**Error Responses**:
- `401 Unauthorized`: 이메일 또는 비밀번호 불일치
  ```json
  {
    "detail": "Incorrect email or password"
  }
  ```

---

### 1.3. Google OAuth 로그인

**Endpoint**: `POST /api/v1/auth/google`

**설명**: Google ID Token을 사용하여 로그인합니다.

**Request Body**:
```json
{
  "token": "google_id_token_here"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@gmail.com",
    "oauth_provider": "google",
    "is_active": true,
    "created_at": "2025-11-30T12:00:00Z"
  }
}
```

**Error Responses**:
- `401 Unauthorized`: Google 토큰 검증 실패

---

### 1.4. 토큰 갱신

**Endpoint**: `POST /api/v1/auth/refresh`

**설명**: Refresh Token을 사용하여 새로운 Access Token을 발급받습니다.

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses**:
- `401 Unauthorized`: Refresh Token 검증 실패

---

### 1.5. 현재 사용자 정보 조회

**Endpoint**: `GET /api/v1/auth/me`

**설명**: 현재 인증된 사용자의 정보를 조회합니다.

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "oauth_provider": null,
  "is_active": true,
  "created_at": "2025-11-30T12:00:00Z"
}
```

**Error Responses**:
- `401 Unauthorized`: 인증 실패 (토큰 없음 또는 만료)
- `404 Not Found`: 사용자를 찾을 수 없음

---

## 2. 동화책 (Storybook)

### 2.1. 동화책 생성 (AI 프롬프트 기반)

**Endpoint**: `POST /api/v1/storybook/create`

**설명**: AI 프롬프트를 사용하여 새로운 동화책을 생성합니다.

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "prompt": "A story about a brave little mouse exploring a magical forest",
  "num_pages": 5,
  "target_age": "5-7",
  "theme": "adventure"
}
```

**Request Schema**:
| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| prompt | string | ✅ | - | 동화책 생성 프롬프트 |
| num_pages | integer | ❌ | 5 | 페이지 수 (1-10) |
| target_age | string | ❌ | "5-7" | 대상 연령 |
| theme | string | ❌ | "adventure" | 테마 |

**Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "The Brave Little Mouse",
  "cover_image": "http://localhost/static/image/550e8400.../cover.png",
  "status": "completed",
  "created_at": "2025-11-30T12:00:00Z",
  "pages": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "sequence": 1,
      "image_url": "http://localhost/static/image/550e8400.../page_1.png",
      "image_prompt": "A small mouse standing at the edge of a magical forest",
      "dialogues": [
        {
          "id": "770e8400-e29b-41d4-a716-446655440002",
          "sequence": 1,
          "speaker": "Narrator",
          "translations": [
            {
              "language_code": "en",
              "text": "Once upon a time, there was a brave little mouse...",
              "is_primary": true
            },
            {
              "language_code": "ko",
              "text": "옛날 옛적에, 용감한 작은 쥐가 있었습니다...",
              "is_primary": false
            }
          ],
          "audios": [
            {
              "language_code": "en",
              "voice_id": "TxWD6rImY3v4izkm2VL0",
              "audio_url": "http://localhost/static/sound/550e8400.../dialogue_1_en.mp3",
              "duration": 3.5
            },
            {
              "language_code": "ko",
              "voice_id": "pNInz6obpgDQGcFmaJgB",
              "audio_url": "http://localhost/static/sound/550e8400.../dialogue_1_ko.mp3",
              "duration": 4.2
            }
          ]
        }
      ]
    }
  ]
}
```

**Error Responses**:
- `401 Unauthorized`: 인증 실패
- `500 Internal Server Error`: 동화책 생성 실패

---

### 2.2. 동화책 생성 (이미지 업로드 기반)

**Endpoint**: `POST /api/v1/storybook/create/with-images`

**설명**: 사용자가 업로드한 이미지와 스토리를 사용하여 동화책을 생성합니다.

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Request Body** (Form Data):
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| stories | string[] | ✅ | 각 페이지의 스토리 텍스트 배열 |
| images | file[] | ✅ | 각 페이지의 이미지 파일 배열 |
| voice_id | string | ❌ | TTS 음성 ID |

**Example (cURL)**:
```bash
curl -X POST "http://localhost/api/v1/storybook/create/with-images" \
  -H "Authorization: Bearer {access_token}" \
  -F "stories=Once upon a time..." \
  -F "stories=The mouse found a magical tree..." \
  -F "images=@page1.png" \
  -F "images=@page2.png" \
  -F "voice_id=TxWD6rImY3v4izkm2VL0"
```

**Response** (201 Created):
동화책 생성 (AI 프롬프트 기반)과 동일한 응답 형식

**Error Responses**:
- `400 Bad Request`: 스토리와 이미지 개수 불일치
- `401 Unauthorized`: 인증 실패
- `500 Internal Server Error`: 동화책 생성 실패

---

### 2.3. 동화책 목록 조회

**Endpoint**: `GET /api/v1/storybook/books`

**설명**: 현재 사용자의 동화책 목록 및 기본 제공 동화책을 조회합니다.

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "The Brave Little Mouse",
    "cover_image": "http://localhost/static/image/550e8400.../cover.png",
    "status": "completed",
    "created_at": "2025-11-30T12:00:00Z",
    "pages": []
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "title": "My Mountain Adventure",
    "cover_image": "http://localhost/static/image/660e8400.../cover.png",
    "status": "completed",
    "created_at": "2025-11-29T10:00:00Z",
    "pages": []
  }
]
```

**Error Responses**:
- `401 Unauthorized`: 인증 실패

---

### 2.4. 동화책 상세 조회

**Endpoint**: `GET /api/v1/storybook/books/{book_id}`

**설명**: 특정 동화책의 상세 정보를 조회합니다.

**Headers**:
```
Authorization: Bearer {access_token}
```

**Path Parameters**:
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| book_id | UUID | 동화책 ID |

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "The Brave Little Mouse",
  "cover_image": "http://localhost/static/image/550e8400.../cover.png",
  "status": "completed",
  "created_at": "2025-11-30T12:00:00Z",
  "pages": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "sequence": 1,
      "image_url": "http://localhost/static/image/550e8400.../page_1.png",
      "image_prompt": "A small mouse standing at the edge of a magical forest",
      "dialogues": [
        {
          "id": "770e8400-e29b-41d4-a716-446655440002",
          "sequence": 1,
          "speaker": "Narrator",
          "translations": [
            {
              "language_code": "en",
              "text": "Once upon a time, there was a brave little mouse...",
              "is_primary": true
            },
            {
              "language_code": "ko",
              "text": "옛날 옛적에, 용감한 작은 쥐가 있었습니다...",
              "is_primary": false
            }
          ],
          "audios": [
            {
              "language_code": "en",
              "voice_id": "TxWD6rImY3v4izkm2VL0",
              "audio_url": "http://localhost/static/sound/550e8400.../dialogue_1_en.mp3",
              "duration": 3.5
            },
            {
              "language_code": "ko",
              "voice_id": "pNInz6obpgDQGcFmaJgB",
              "audio_url": "http://localhost/static/sound/550e8400.../dialogue_1_ko.mp3",
              "duration": 4.2
            }
          ]
        }
      ]
    }
  ]
}
```

**Error Responses**:
- `401 Unauthorized`: 인증 실패
- `403 Forbidden`: 권한 없음 (다른 사용자의 동화책)
- `404 Not Found`: 동화책을 찾을 수 없음

---

### 2.5. 동화책 삭제

**Endpoint**: `DELETE /api/v1/storybook/books/{book_id}`

**설명**: 동화책을 삭제합니다.

**Headers**:
```
Authorization: Bearer {access_token}
```

**Path Parameters**:
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| book_id | UUID | 동화책 ID |

**Response** (204 No Content):
```
(응답 본문 없음)
```

**Error Responses**:
- `401 Unauthorized`: 인증 실패
- `404 Not Found`: 동화책을 찾을 수 없음 또는 권한 없음

---

## 3. TTS (Text-to-Speech)

### 3.1. 음성 생성

**Endpoint**: `POST /api/v1/tts/generate`

**설명**: 텍스트를 음성으로 변환합니다.

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "text": "Hello, this is a test message.",
  "voice_id": "TxWD6rImY3v4izkm2VL0",
  "model_id": "eleven_v3"
}
```

**Request Schema**:
| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| text | string | ✅ | - | 변환할 텍스트 |
| voice_id | string | ❌ | "TxWD6rImY3v4izkm2VL0" | ElevenLabs 음성 ID |
| model_id | string | ❌ | "eleven_v3" | TTS 모델 ID |

**Response** (201 Created):
```json
{
  "audio_url": "http://localhost/static/sound/550e8400.../audio.mp3",
  "text": "Hello, this is a test message.",
  "voice_id": "TxWD6rImY3v4izkm2VL0",
  "duration": 3.5
}
```

**Error Responses**:
- `401 Unauthorized`: 인증 실패
- `500 Internal Server Error`: 음성 생성 실패

---

### 3.2. 사용 가능한 음성 목록 조회

**Endpoint**: `GET /api/v1/tts/voices`

**설명**: 사용 가능한 TTS 음성 목록을 조회합니다.

**Response** (200 OK):
```json
[
  {
    "voice_id": "TxWD6rImY3v4izkm2VL0",
    "name": "Rachel",
    "language": "en",
    "gender": "female"
  },
  {
    "voice_id": "pNInz6obpgDQGcFmaJgB",
    "name": "Adam",
    "language": "en",
    "gender": "male"
  }
]
```

---

## 4. 사용자 (User)

### 4.1. 내 정보 조회

**Endpoint**: `GET /api/v1/user/me`

**설명**: 현재 인증된 사용자의 정보를 조회합니다.

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "oauth_provider": null,
  "is_active": true,
  "created_at": "2025-11-30T12:00:00Z"
}
```

**Error Responses**:
- `401 Unauthorized`: 인증 실패

---

### 4.2. 내 정보 수정

**Endpoint**: `PUT /api/v1/user/me`

**설명**: 현재 사용자의 정보를 수정합니다.

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "password": "newSecurePassword123!"
}
```

**Request Schema**:
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| password | string | ❌ | 새로운 비밀번호 (최소 8자) |

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "oauth_provider": null,
  "is_active": true,
  "created_at": "2025-11-30T12:00:00Z"
}
```

**Error Responses**:
- `401 Unauthorized`: 인증 실패

---

### 4.3. 회원 탈퇴

**Endpoint**: `DELETE /api/v1/user/me`

**설명**: 현재 사용자의 계정을 삭제합니다.

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response** (204 No Content):
```
(응답 본문 없음)
```

**Error Responses**:
- `401 Unauthorized`: 인증 실패

---

## 5. 공통 응답 형식

### 성공 응답
모든 성공 응답은 적절한 HTTP 상태 코드와 함께 JSON 형식으로 반환됩니다.

### 에러 응답
모든 에러 응답은 다음 형식을 따릅니다:

```json
{
  "detail": "에러 메시지"
}
```

---

## 6. 에러 코드

| HTTP 상태 코드 | 설명 | 예시 |
|----------------|------|------|
| 200 OK | 요청 성공 | 데이터 조회 성공 |
| 201 Created | 리소스 생성 성공 | 동화책 생성 성공 |
| 204 No Content | 요청 성공 (응답 본문 없음) | 삭제 성공 |
| 400 Bad Request | 잘못된 요청 | 유효성 검증 실패 |
| 401 Unauthorized | 인증 실패 | 토큰 없음 또는 만료 |
| 403 Forbidden | 권한 없음 | 다른 사용자의 리소스 접근 시도 |
| 404 Not Found | 리소스를 찾을 수 없음 | 존재하지 않는 동화책 ID |
| 500 Internal Server Error | 서버 에러 | AI 생성 실패 등 |

---

## 7. 인증 방식

### JWT (JSON Web Token)

모든 보호된 엔드포인트는 JWT 인증을 사용합니다.

**Header 형식**:
```
Authorization: Bearer {access_token}
```

**토큰 만료 시간**:
- Access Token: 15분
- Refresh Token: 7일

**토큰 갱신**:
Access Token이 만료되면 `/api/v1/auth/refresh` 엔드포인트를 사용하여 새로운 Access Token을 발급받습니다.

---

## 8. 페이지네이션

현재 API는 페이지네이션을 지원하지 않습니다. 향후 버전에서 추가될 예정입니다.

---

## 9. Rate Limiting

현재 API는 Rate Limiting을 적용하지 않습니다. 프로덕션 환경에서는 적절한 Rate Limiting을 설정할 예정입니다.

---

## 10. CORS

개발 환경에서는 다음 Origin을 허용합니다:
- `http://localhost:5173`
- `http://localhost:5174`

프로덕션 환경에서는 환경 변수 `CORS_ORIGINS`를 통해 설정합니다.

---

## 11. Swagger UI

API 문서는 Swagger UI를 통해 확인할 수 있습니다:

**개발 환경**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**프로덕션 환경**:
- Swagger UI는 비활성화됩니다 (`DEBUG=false`).

---

## 12. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|-----------|
| 2025-12-02 | v1.1 | 다국어 지원 구조 업데이트 (Dialogue 응답 형식 변경) |
| 2025-11-30 | v1.0 | 초기 API 명세 작성 |

---

## 13. 문의

API 관련 문의사항은 개발팀에 문의해주세요.
