# TTS 비동기 워커 아키텍처

이 문서는 프로젝트의 TTS(Text-to-Speech) 기능과 비동기 워커 아키텍처 관련 파일들을 설명합니다.

---

## 아키텍처 개요

본 프로젝트는 **Celery 없이 Redis Streams + asyncio 기반의 순수 비동기 구현**을 사용합니다.

### 핵심 특징

- **Producer-Consumer 패턴**: 작업 분배
- **Semaphore 기반 동시성 제어**: 최대 3개 동시 처리
- **Consumer Group**: 메시지 ACK 처리
- **이벤트 기반 아키텍처**: Redis Streams를 통한 pub/sub

---

## 1. TTS 기능 핵심 파일

**위치:** `backend/features/tts/`

| 파일 | 역할 |
|------|------|
| `worker.py` | TTS Worker (Consumer) - Redis Streams에서 작업을 소비하고 ElevenLabs API 호출 처리. 세마포어로 동시 3개 제한 |
| `producer.py` | TTS Producer - Redis Streams에 TTS 생성 작업을 큐에 추가 |
| `service.py` | TTSService - TTS 비즈니스 로직, 캐싱, 분산 락 관리 |
| `models.py` | Audio, Voice SQLAlchemy ORM 모델. VoiceStatus(processing/completed/failed), VoiceVisibility(private/public/default) 정의 |
| `repository.py` | 데이터베이스 접근 레이어 (AudioRepository, VoiceRepository) |
| `schemas.py` | Pydantic 요청/응답 스키마 (GenerateSpeechRequest, AudioResponse, VoiceResponse 등) |
| `exceptions.py` | TTS 관련 예외 정의 (TTSGenerationFailedException, TTSUploadFailedException 등) |
| `dependencies.py` | 의존성 주입 설정 |

---

## 2. 이벤트 버스 시스템

**위치:** `backend/core/events/`

| 파일 | 역할 |
|------|------|
| `redis_streams_bus.py` | Redis Streams 기반 이벤트 버스 구현. Consumer Group 패턴 사용, 메시지 ACK 처리 |
| `bus.py` | EventBus 추상 인터페이스 (publish/subscribe/start/stop 메서드 정의) |
| `types.py` | 이벤트 타입 정의 - `EventType` enum (TTS_CREATION, VOICE_CREATED, VOICE_UPDATED, VOICE_DELETED) |
| `__init__.py` | 이벤트 모듈 초기화 |

---

## 3. 태스크 큐 시스템

**위치:** `backend/core/tasks/`

| 파일 | 역할 |
|------|------|
| `voice_queue.py` | VoiceSyncQueue - Redis Set 기반 태스크 큐. TTL 및 상태 추적으로 Voice 동기화 작업 큐 관리 |
| `voice_sync.py` | 백그라운드 스케줄링 태스크. ElevenLabs API로부터 주기적으로 음성 상태 동기화. 타임아웃 처리(최대 30분) 및 Voice 미리보기 TTS 생성 트리거 |
| `__init__.py` | 태스크 모듈 초기화 |

---

## 4. API 엔드포인트

**위치:** `backend/api/v1/endpoints/`

| 파일 | 역할 |
|------|------|
| `tts.py` | FastAPI 라우터 - 음성 생성, 음성 관리, 음성 복제, 음성 목록 조회 등 TTS 관련 엔드포인트 |

---

## 5. AI 프로바이더

**위치:** `backend/infrastructure/ai/providers/`

| 파일 | 역할 |
|------|------|
| `elevenlabs_tts.py` | ElevenLabs TTS Provider 구현. 스마트 모델 선택, 발음 사전 지원, 음성 복제, 사용자 할당량 관리 기능 |

---

## 6. 애플리케이션 라이프사이클

**위치:** `backend/`

| 파일 | 역할 |
|------|------|
| `main.py` | FastAPI 애플리케이션 진입점. asynccontextmanager를 사용한 라이프사이클 관리 - 이벤트 버스 시작, Voice Sync Task 시작, TTS Worker 시작/종료 |

---

## 7. 설정 파일

**위치:** `backend/core/`

| 파일 | 역할 |
|------|------|
| `config.py` | Pydantic Settings v2 기반 중앙 설정. Redis URL, TTS 프로바이더 설정(ElevenLabs API 키, 기본 음성 ID, 모델 ID, 발음 사전), 언어 지원 설정 포함 |

---

## 8. Storybook 태스크 연동

**위치:** `backend/features/storybook/tasks/`

| 파일 | 역할 |
|------|------|
| `core.py` | Storybook 태스크 정의. TTSProducer를 사용하여 대화 오디오 TTS 생성 요청 |
| `runner.py` | 태스크 실행 러너 및 오케스트레이션 로직 |
| `store.py` | 태스크 상태 및 컨텍스트 관리 |
| `retry.py` | 실패한 태스크에 대한 재시도 로직 및 배치 재시도 추적 |
| `schemas.py` | 태스크 관련 Pydantic 스키마 |

---

## 9. 테스트 파일

**위치:** `backend/tests/`

| 파일 | 역할 |
|------|------|
| `test_voice_queue.py` | VoiceSyncQueue 기능 단위 테스트 |
| `test_tts_service_voice.py` | TTS 서비스 음성 작업 단위 테스트 |
| `test_tts_caching.py` | TTS 캐싱 메커니즘 통합 테스트 |

---

## 10. 주요 의존성

`requirements.txt`에서 비동기 및 큐 관련 주요 패키지:

```
redis[hiredis]==5.0.1          # Redis 비동기 클라이언트 (aioredis 대체)
aiocache==0.12.2               # Redis 백엔드 비동기 캐싱
aiohttp==3.9.1                 # 비동기 HTTP 클라이언트
aiofiles==23.2.1               # 비동기 파일 작업
pytest-asyncio==0.21.1         # 비동기 pytest 지원
elevenlabs>=0.2.0              # ElevenLabs TTS SDK
asyncpg                        # 비동기 PostgreSQL 드라이버
```

---

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
│                           (main.py)                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
        ┌───────────────────┐   ┌───────────────────────┐
        │   TTS Endpoint    │   │   Storybook Tasks     │
        │  (api/v1/tts.py)  │   │ (storybook/tasks/)    │
        └───────────────────┘   └───────────────────────┘
                    │                       │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │     TTSProducer       │
                    │   (tts/producer.py)   │
                    └───────────────────────┘
                                │
                                ▼ publish
                    ┌───────────────────────┐
                    │  RedisStreamsEventBus │
                    │ (core/events/redis_   │
                    │   streams_bus.py)     │
                    └───────────────────────┘
                                │
                                ▼ consume (Consumer Group)
                    ┌───────────────────────┐
                    │      TTSWorker        │
                    │   (tts/worker.py)     │
                    │  Semaphore(3) 동시성   │
                    └───────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
        ┌───────────────────┐   ┌───────────────────────┐
        │    TTSService     │   │   ElevenLabs TTS      │
        │ (tts/service.py)  │   │ Provider (elevenlabs_ │
        │                   │   │      tts.py)          │
        └───────────────────┘   └───────────────────────┘
                    │
                    ▼
        ┌───────────────────┐
        │   AudioRepository │
        │ (tts/repository)  │
        └───────────────────┘
```

---

## 데이터 흐름

1. **요청 수신**: API 엔드포인트 또는 Storybook 태스크에서 TTS 생성 요청
2. **작업 큐잉**: TTSProducer가 Redis Streams에 TTS_CREATION 이벤트 발행
3. **작업 소비**: TTSWorker가 Consumer Group을 통해 메시지 수신
4. **동시성 제어**: Semaphore(3)로 동시 처리 제한
5. **TTS 생성**: ElevenLabs API 호출하여 오디오 생성
6. **저장**: 생성된 오디오를 스토리지에 저장하고 DB에 메타데이터 기록
7. **완료**: 메시지 ACK 처리
