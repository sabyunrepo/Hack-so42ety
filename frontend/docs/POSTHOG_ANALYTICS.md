# PostHog Analytics 통합 가이드

## 1. 개요

### 1.1 PostHog란?
PostHog는 오픈소스 제품 분석 플랫폼으로, 사용자 행동 추적, 세션 리플레이, A/B 테스트 등을 제공합니다.

### 1.2 도입 목적
| 목적 | 설명 |
|------|------|
| 사용자 행동 분석 | 페이지뷰, 클릭, 전환율 등 핵심 지표 추적 |
| 제품 개선 | 데이터 기반 UX/UI 의사결정 |
| 문제 진단 | 사용자 이탈 지점 파악 |

### 1.3 적용 범위
- **적용**: `frontend/` (React + Vite)
- **제외**: `ai-playground/`
- **활성화 조건**: Production 환경에서만 동작

---

## 2. 구현 방식

### 2.1 공식 PostHog React SDK 사용
공식 문서 권장 방식을 따릅니다:
- `posthog-js` - 코어 SDK
- `@posthog/react` - React Provider 및 Hooks

### 2.2 패키지
```bash
npm install posthog-js @posthog/react
```

### 2.3 파일 구조
```
frontend/src/
└── main.tsx    # PostHog 초기화 및 Provider 통합
```

### 2.4 초기화 방식
```tsx
import posthog from "posthog-js";
import { PostHogProvider } from "@posthog/react";

// Production에서만 초기화
if (import.meta.env.PROD && import.meta.env.VITE_PUBLIC_POSTHOG_KEY) {
  posthog.init(import.meta.env.VITE_PUBLIC_POSTHOG_KEY, {
    api_host: import.meta.env.VITE_PUBLIC_POSTHOG_HOST,
    defaults: "2025-05-24",
  });
}

<PostHogProvider client={posthog}>
  <App />
</PostHogProvider>
```

### 2.5 환경 분리
| 실행 방식 | `import.meta.env.PROD` | PostHog 상태 |
|----------|------------------------|-------------|
| `npm run dev` | `false` | 초기화 안됨 |
| `make dev` | `false` | 초기화 안됨 |
| `make prod` | `true` | 초기화됨 |

---

## 3. 환경 변수

### 3.1 변수 목록
| 변수명 | 필수 | 설명 | 기본값 |
|--------|------|------|--------|
| `VITE_PUBLIC_POSTHOG_KEY` | Yes | PostHog 프로젝트 API 키 | - |
| `VITE_PUBLIC_POSTHOG_HOST` | No | PostHog 인스턴스 URL | `https://us.i.posthog.com` |

### 3.2 설정 위치
| 환경 | 파일 | 설명 |
|------|------|------|
| Production | `/.env` | Docker 빌드 시 사용 |
| Local Dev | 불필요 | 자동 비활성화 |

### 3.3 Docker 빌드 흐름
```
.env (VITE_PUBLIC_POSTHOG_KEY)
    ↓
docker-compose.prod.yml (build args)
    ↓
Dockerfile (ARG → ENV)
    ↓
npm run build (환경 변수 번들링)
```

---

## 4. 설정 방법

### 4.1 PostHog Cloud 설정
1. [PostHog Cloud](https://app.posthog.com) 접속
2. 프로젝트 생성 또는 선택
3. Settings > Project > Project API Key 복사

### 4.2 환경 변수 추가
프로젝트 루트 `.env` 파일에 추가:
```bash
VITE_PUBLIC_POSTHOG_KEY=phc_your_project_api_key
VITE_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com
```

### 4.3 프로덕션 배포
```bash
make prod
```

---

## 5. 자동 추적 기능

PostHog SDK가 자동으로 추적하는 이벤트:

| 이벤트 | 설명 |
|--------|------|
| `$pageview` | 페이지 조회 |
| `$pageleave` | 페이지 이탈 |
| `$autocapture` | 클릭, 입력 등 자동 캡처 |

---

## 6. 수동 이벤트 추적

### 6.1 usePostHog Hook 사용
```tsx
import { usePostHog } from "@posthog/react";

function MyComponent() {
  const posthog = usePostHog();

  const handleClick = () => {
    posthog?.capture("button_clicked", { button_name: "create" });
  };

  // 사용자 식별
  useEffect(() => {
    if (user) {
      posthog?.identify(user.id, { email: user.email });
    }
  }, [user, posthog]);
}
```

### 6.2 구현된 커스텀 이벤트

#### 인증 (LoginPage.tsx)
| 이벤트명 | 설명 | 속성 |
|----------|------|------|
| `login_success` | 이메일 로그인 성공 | `{ method: "email" }` |

#### 동화책 생성 (Creator.tsx)
| 이벤트명 | 설명 | 속성 |
|----------|------|------|
| `book_creation_requested` | 동화책 생성 요청 (서버에서 비동기 처리) | `{ page_count }` |

#### 동화책 뷰어 (Viewer.tsx)
| 이벤트명 | 설명 | 속성 |
|----------|------|------|
| `book_viewed` | 동화책 열람 | `{ book_id, page_count }` |
| `page_turned` | 페이지 넘김 | `{ book_id, page_number }` |

#### 책장 (Bookshelf.tsx)
| 이벤트명 | 설명 | 속성 |
|----------|------|------|
| `book_deleted` | 동화책 삭제 | `{ book_id }` |

#### 설정 (Settings.tsx)
| 이벤트명 | 설명 | 속성 |
|----------|------|------|
| `voice_file_uploaded` | 음성 파일 업로드 성공 | `{ file_type, file_size_mb }` |
| `voice_creation_requested` | 목소리 생성 요청 | `{ voice_name }` |

---

## 7. 검증 방법

| 환경 | 확인 사항 |
|------|----------|
| Development | `posthog.init()` 호출되지 않음 (정상) |
| Production | PostHog 대시보드에서 이벤트 수신 확인 |

---

## 8. 참고 자료

| 자료 | 링크 |
|------|------|
| PostHog 공식 문서 | https://posthog.com/docs |
| React 통합 가이드 | https://posthog.com/docs/libraries/react |
| 이벤트 설계 가이드 | https://posthog.com/docs/data/events |

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2024-12-17 | 1.0.0 | 최초 작성 (커스텀 Context 방식) |
| 2024-12-17 | 2.0.0 | 공식 SDK 방식으로 변경 |
| 2024-12-17 | 2.1.0 | `@posthog/react` 패키지 적용, `posthog.init()` 방식으로 변경 |
| 2024-12-18 | 2.2.0 | 커스텀 이벤트 추적 구현 (login, book, voice 관련 이벤트) |
