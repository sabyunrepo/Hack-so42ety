# 백엔드 캐싱 전략 분석 및 추천

## 📊 현재 환경 분석

### 기술 스택
- **프레임워크**: FastAPI (Python)
- **데이터베이스**: PostgreSQL
- **인프라**: Docker Compose
- **외부 API**: ElevenLabs TTS, Google Gemini, Kling AI
- **현재 캐싱**: `functools.lru_cache` (AIProviderFactory에만 사용)

### 캐싱이 필요한 주요 영역

1. **TTS Voices 목록** (`/api/v1/tts/voices`)
   - 호출 빈도: 높음 (모든 사용자가 새 책 만들기 시 호출)
   - 변경 빈도: 낮음 (음성 목록은 자주 변하지 않음)
   - 데이터 크기: 중간 (~20-30개 음성 정보)
   - 캐시 적합도: ⭐⭐⭐⭐⭐

2. **AI 스토리 생성** (Google Gemini)
   - 호출 빈도: 중간 (책 생성 시)
   - 변경 빈도: 없음 (같은 프롬프트면 같은 결과)
   - 데이터 크기: 작음 (텍스트)
   - 캐시 적합도: ⭐⭐⭐⭐

3. **이미지 생성** (Kling AI)
   - 호출 빈도: 중간 (책 생성 시)
   - 변경 빈도: 없음 (같은 프롬프트면 같은 결과)
   - 데이터 크기: 큼 (이미지 URL)
   - 캐시 적합도: ⭐⭐⭐

4. **사용자 정보** (JWT 토큰 기반)
   - 호출 빈도: 높음 (모든 인증된 요청)
   - 변경 빈도: 낮음
   - 데이터 크기: 작음
   - 캐시 적합도: ⭐⭐⭐

---

## 🔍 캐싱 방법 비교 분석

### 1. In-Memory 캐싱 (Python 내장)

#### 방법
- `functools.lru_cache` (동기 함수용)
- `cachetools` 라이브러리 (비동기 지원, TTL 지원)
- Python `dict` + 수동 관리

#### 장점 ✅
- **구현 간단**: 추가 인프라 불필요
- **성능 우수**: 메모리 직접 접근, 매우 빠름
- **의존성 없음**: 외부 서비스 불필요
- **비용 없음**: 추가 리소스 불필요

#### 단점 ❌
- **단일 인스턴스만**: Docker 컨테이너 여러 개면 캐시 공유 안 됨
- **메모리 제한**: 서버 재시작 시 캐시 초기화
- **확장성 제한**: 수평 확장 시 각 인스턴스가 독립 캐시
- **TTL 관리 어려움**: 수동으로 만료 시간 관리 필요

#### 사용 사례
- 단일 인스턴스 환경
- 빠른 프로토타입
- 임시 캐싱 (예: AIProviderFactory)

#### 코드 예시
```python
from cachetools import TTLCache
from functools import wraps

# TTL 캐시 생성 (최대 100개, 1시간 TTL)
cache = TTLCache(maxsize=100, ttl=3600)

@wraps
async def cached_get_voices():
    cache_key = "tts:voices"
    if cache_key in cache:
        return cache[cache_key]
    # API 호출
    result = await api_call()
    cache[cache_key] = result
    return result
```

---

### 2. Redis 캐싱

#### 방법
- Redis 서버 추가 (Docker Compose)
- `redis` 또는 `aioredis` 라이브러리 사용
- 분산 캐싱 지원

#### 장점 ✅
- **분산 캐싱**: 여러 인스턴스 간 캐시 공유
- **TTL 자동 관리**: 만료 시간 자동 처리
- **고성능**: 메모리 기반, 매우 빠름
- **확장성**: 수평 확장에 적합
- **영속성 옵션**: 필요 시 디스크 저장 가능
- **다양한 데이터 타입**: String, Hash, List, Set 등

#### 단점 ❌
- **추가 인프라**: Redis 서버 필요
- **메모리 사용**: 별도 메모리 할당 필요
- **의존성 증가**: Redis 서버 장애 시 영향
- **설정 복잡도**: 네트워크, 보안 설정 필요

#### 사용 사례
- 프로덕션 환경
- 다중 인스턴스 배포
- 장기 캐싱 필요
- 복잡한 캐시 전략

#### 코드 예시
```python
import aioredis
from json import dumps, loads

redis_client = await aioredis.from_url("redis://redis:6379")

async def cached_get_voices():
    cache_key = "tts:voices"
    cached = await redis_client.get(cache_key)
    if cached:
        return loads(cached)
    # API 호출
    result = await api_call()
    await redis_client.setex(cache_key, 3600, dumps(result))
    return result
```

---

### 3. 데이터베이스 캐싱

#### 방법
- PostgreSQL에 캐시 테이블 생성
- 캐시 키-값 저장
- TTL은 `created_at`으로 관리

#### 장점 ✅
- **인프라 추가 불필요**: 기존 DB 활용
- **영속성**: 서버 재시작해도 유지
- **트랜잭션 지원**: DB 트랜잭션과 통합 가능

#### 단점 ❌
- **성능 낮음**: 디스크 I/O, 네트워크 지연
- **DB 부하 증가**: 캐시 조회도 DB 쿼리
- **확장성 제한**: DB 성능에 의존
- **TTL 관리 복잡**: 수동으로 만료 데이터 삭제 필요

#### 사용 사례
- 캐시 데이터가 매우 중요할 때
- 영속성이 필수일 때
- Redis 등 추가 인프라 불가능할 때

---

### 4. HTTP 캐시 헤더

#### 방법
- FastAPI 응답에 `Cache-Control` 헤더 추가
- 프론트엔드/프록시에서 캐싱

#### 장점 ✅
- **구현 간단**: 헤더만 추가
- **클라이언트 캐싱**: 네트워크 요청 감소
- **CDN 활용**: CDN에서 캐싱 가능

#### 단점 ❌
- **서버 부하 감소 없음**: 첫 요청은 여전히 서버 처리
- **제어 제한**: 클라이언트가 캐시 무시 가능
- **동적 데이터 부적합**: 사용자별 데이터는 어려움

#### 사용 사례
- 정적/반정적 데이터
- CDN 활용 시
- 클라이언트 캐싱 보완

---

## 🎯 추천 전략 (단계별)

### Phase 1: 즉시 적용 (In-Memory 캐싱)

**대상**: TTS Voices 목록

**이유**:
- 구현이 가장 간단
- 현재 단일 인스턴스 환경
- 빠른 효과

**구현**:
```python
# cachetools 사용
from cachetools import TTLCache
from functools import wraps

voices_cache = TTLCache(maxsize=1, ttl=3600)  # 1시간 TTL
```

**예상 효과**:
- ElevenLabs API 호출 99% 감소
- 응답 시간 10배 개선 (API 호출 → 메모리 접근)

---

### Phase 2: 프로덕션 준비 (Redis 캐싱)

**대상**: 모든 외부 API 호출 결과

**이유**:
- 수평 확장 대비
- 더 정교한 캐시 관리
- 프로덕션 환경 적합

**구현**:
1. Docker Compose에 Redis 추가
2. `aioredis` 라이브러리 추가
3. 캐시 레이어 추상화

**예상 효과**:
- 모든 인스턴스 간 캐시 공유
- 외부 API 호출 대폭 감소
- 비용 절감 (API 사용량 감소)

---

### Phase 3: 고급 최적화 (하이브리드)

**대상**: AI 생성 결과 (스토리, 이미지)

**이유**:
- 같은 프롬프트면 같은 결과
- 생성 비용이 높음
- 사용자 간 공유 가능

**구현**:
- 프롬프트 해시를 키로 사용
- Redis + In-Memory 하이브리드
- 캐시 히트율 모니터링

---

## 📋 최종 추천: 하이브리드 접근

### 즉시 적용 (Phase 1)
**In-Memory 캐싱 (cachetools)**
- TTS Voices 목록
- 구현 시간: 1-2시간
- 효과: 즉시

### 단기 적용 (Phase 2)
**Redis 캐싱**
- 모든 외부 API 호출
- 구현 시간: 4-6시간
- 효과: 프로덕션 준비

### 장기 적용 (Phase 3)
**하이브리드 + 모니터링**
- AI 생성 결과 캐싱
- 캐시 히트율 모니터링
- 구현 시간: 1-2일
- 효과: 최적화

---

## 💡 구체적 구현 방안

### Option A: In-Memory만 사용 (빠른 시작)

**장점**:
- 즉시 적용 가능
- 추가 인프라 불필요
- 구현 간단

**단점**:
- 단일 인스턴스만
- 서버 재시작 시 초기화

**추천 시나리오**:
- 개발/스테이징 환경
- 단일 인스턴스 프로덕션
- 빠른 프로토타입

---

### Option B: Redis 사용 (프로덕션 권장)

**장점**:
- 분산 캐싱
- 영속성
- 확장성

**단점**:
- 추가 인프라
- 설정 복잡도

**추천 시나리오**:
- 프로덕션 환경
- 다중 인스턴스 배포
- 장기 운영

---

### Option C: 하이브리드 (최적)

**구성**:
- L1: In-Memory (빠른 접근)
- L2: Redis (분산 캐싱)

**장점**:
- 최고 성능
- 확장성
- 유연성

**단점**:
- 구현 복잡도
- 두 가지 캐시 관리

**추천 시나리오**:
- 대규모 트래픽
- 성능 최적화 필요
- 장기 운영

---

## 🔧 구현 우선순위

### 1순위: TTS Voices 캐싱 (In-Memory)
- **영향도**: 높음 (모든 사용자)
- **구현 난이도**: 낮음
- **예상 효과**: API 호출 99% 감소

### 2순위: Redis 인프라 구축
- **영향도**: 전체 시스템
- **구현 난이도**: 중간
- **예상 효과**: 확장성 확보

### 3순위: AI 생성 결과 캐싱
- **영향도**: 중간 (책 생성 시)
- **구현 난이도**: 높음
- **예상 효과**: 비용 절감

---

## 📊 예상 효과

### In-Memory 캐싱만 (Phase 1)
- **TTS Voices API 호출**: 99% 감소
- **응답 시간**: 10배 개선
- **구현 시간**: 1-2시간

### Redis 추가 (Phase 2)
- **모든 외부 API 호출**: 80-90% 감소
- **서버 부하**: 50% 감소
- **비용 절감**: API 사용량 대폭 감소
- **구현 시간**: 4-6시간

### 하이브리드 최적화 (Phase 3)
- **전체 성능**: 2-3배 개선
- **비용 절감**: 60-70% 감소
- **사용자 경험**: 대폭 개선
- **구현 시간**: 1-2일

---

## 🎯 최종 추천

### 현재 환경 기준: **Option B (Redis)**

**이유**:
1. **프로덕션 준비**: 수평 확장 대비
2. **구현 난이도 적절**: 복잡하지만 관리 가능
3. **효과 극대화**: 모든 외부 API 호출 캐싱
4. **장기 운영**: 확장성과 유지보수성

**구현 순서**:
1. **즉시**: In-Memory로 TTS Voices 캐싱 (빠른 효과)
2. **단기**: Redis 인프라 구축 및 마이그레이션
3. **장기**: AI 생성 결과 캐싱 추가

**예상 투자 대비 효과**:
- 구현 시간: 1일
- 인프라 비용: Redis 메모리 (~100MB)
- 효과: API 호출 80-90% 감소, 응답 시간 5-10배 개선

---

## 🔄 캐시 무효화 전략 (Cache Invalidation)

### 문제 시나리오

**현재 상황**:
1. 사용자가 `/api/v1/tts/voices` 호출 → 캐시에 저장
2. 사용자가 Voice Clone 생성 (`/api/v1/tts/clone/create`)
3. ElevenLabs에 새 음성이 추가됨
4. 사용자가 다시 `/api/v1/tts/voices` 호출
5. **문제**: 캐시된 이전 목록이 반환되어 새 음성이 보이지 않음

### 캐시 무효화 방법 비교

#### 1. Write-Invalidate (쓰기 시 무효화) ⭐⭐⭐⭐⭐

**방법**:
- Voice 생성/수정/삭제 시 관련 캐시 키 삭제
- 가장 직관적이고 효과적

**장점**:
- 즉시 반영: 쓰기 직후 캐시 무효화
- 정확성: 데이터 일관성 보장
- 구현 간단: 명시적 무효화

**단점**:
- 모든 쓰기 작업에 무효화 로직 추가 필요
- 여러 캐시 키 관리 필요

**구현 예시**:
```python
# Voice 생성 후
async def create_voice_clone(...):
    # Voice 생성 로직
    voice = await elevenlabs_api.create_voice(...)
    
    # 캐시 무효화
    await cache.delete("tts:voices")
    
    return voice
```

---

#### 2. Tag-based Invalidation (태그 기반 무효화) ⭐⭐⭐⭐

**방법**:
- 캐시 키에 태그를 부여하고, 태그 단위로 무효화
- 예: `tts:voices` → 태그: `voices`

**장점**:
- 유연성: 여러 캐시 키를 한 번에 무효화
- 확장성: 새로운 캐시 추가 시 태그만 추가

**단점**:
- 구현 복잡도 증가
- Redis의 경우 태그 관리 추가 로직 필요

**구현 예시**:
```python
# 캐시 저장 시 태그 추가
await cache.set("tts:voices", data, tags=["voices"])

# 무효화 시 태그로 삭제
await cache.delete_by_tag("voices")
```

---

#### 3. TTL + Manual Invalidation (하이브리드) ⭐⭐⭐⭐⭐

**방법**:
- 기본적으로 TTL 기반 자동 만료
- 중요한 쓰기 작업 시 수동 무효화

**장점**:
- 안전성: TTL로 최대한 오래된 데이터 방지
- 정확성: 중요한 변경 시 즉시 반영
- 균형: 성능과 일관성의 균형

**단점**:
- 두 가지 메커니즘 관리 필요

**구현 예시**:
```python
# TTL 1시간 + 수동 무효화
await cache.set("tts:voices", data, ttl=3600)

# Voice 생성 시 즉시 무효화
async def create_voice_clone(...):
    voice = await create_voice(...)
    await cache.delete("tts:voices")  # 즉시 무효화
    return voice
```

---

#### 4. Event-driven Invalidation (이벤트 기반) ⭐⭐⭐

**방법**:
- 이벤트 버스나 메시지 큐 사용
- 쓰기 작업이 이벤트 발행, 캐시가 구독하여 무효화

**장점**:
- 느슨한 결합: 서비스 간 의존성 감소
- 확장성: 여러 서비스가 동일 이벤트 구독 가능

**단점**:
- 구현 복잡도 높음
- 추가 인프라 필요 (메시지 큐 등)
- 오버엔지니어링 가능성

---

### 추천 전략: TTL + Write-Invalidate (하이브리드)

**이유**:
1. **안전성**: TTL로 오래된 데이터 방지
2. **정확성**: 중요한 변경 시 즉시 반영
3. **구현 간단**: 복잡한 인프라 불필요
4. **균형**: 성능과 일관성의 최적 균형

---

## 🎯 캐시 무효화 구현 전략

### Phase 1: 기본 무효화 (즉시 적용)

**대상**: TTS Voices 목록

**구현**:
```python
# 캐시 키 정의
CACHE_KEY_VOICES = "tts:voices"
CACHE_TTL_VOICES = 3600  # 1시간

# 조회 시 캐시 사용
async def get_voices():
    cached = await cache.get(CACHE_KEY_VOICES)
    if cached:
        return cached
    
    voices = await elevenlabs_api.get_voices()
    await cache.set(CACHE_KEY_VOICES, voices, ttl=CACHE_TTL_VOICES)
    return voices

# Voice 생성 시 무효화
async def create_voice_clone(...):
    voice = await elevenlabs_api.create_voice(...)
    await cache.delete(CACHE_KEY_VOICES)  # 즉시 무효화
    return voice
```

**무효화가 필요한 작업**:
- ✅ Voice Clone 생성 (`POST /tts/clone/create`)
- ✅ Voice 삭제 (`DELETE /tts/clone/{voice_id}`) - 추후 구현 시
- ✅ Voice 수정 (`PUT /tts/clone/{voice_id}`) - 추후 구현 시

---

### Phase 2: 고급 무효화 (태그 기반)

**대상**: 여러 관련 캐시

**구현**:
```python
# 태그 기반 캐시 관리
CACHE_TAG_VOICES = "voices"

async def get_voices():
    cached = await cache.get(CACHE_KEY_VOICES)
    if cached:
        return cached
    
    voices = await elevenlabs_api.get_voices()
    await cache.set(
        CACHE_KEY_VOICES, 
        voices, 
        ttl=CACHE_TTL_VOICES,
        tags=[CACHE_TAG_VOICES]
    )
    return voices

# Voice 생성 시 태그로 무효화
async def create_voice_clone(...):
    voice = await elevenlabs_api.create_voice(...)
    await cache.delete_by_tag(CACHE_TAG_VOICES)  # 모든 voices 관련 캐시 무효화
    return voice
```

---

### Phase 3: 이벤트 기반 (선택적)

**대상**: 복잡한 캐시 의존성

**구현**:
- Redis Pub/Sub 또는 메시지 큐 사용
- Voice 생성 이벤트 발행
- 캐시 서비스가 구독하여 무효화

---

## 📋 캐시 무효화 체크리스트

### TTS Voices 캐싱

#### 캐시 저장
- [x] `GET /api/v1/tts/voices` 호출 시 캐시 저장
- [x] TTL 설정 (1시간)

#### 캐시 무효화 필요 작업
- [ ] `POST /api/v1/tts/clone/create` - Voice 생성 시
- [ ] `DELETE /api/v1/tts/clone/{voice_id}` - Voice 삭제 시 (추후)
- [ ] `PUT /api/v1/tts/clone/{voice_id}` - Voice 수정 시 (추후)

#### 무효화 방법
- **즉시 무효화**: Write-Invalidate 패턴
- **안전장치**: TTL (최대 1시간 후 자동 갱신)

---

## 🔧 구체적 구현 방안

### Option A: In-Memory + 수동 무효화

**구현**:
```python
from cachetools import TTLCache

voices_cache = TTLCache(maxsize=1, ttl=3600)

async def get_voices():
    if "voices" in voices_cache:
        return voices_cache["voices"]
    
    voices = await api_call()
    voices_cache["voices"] = voices
    return voices

async def create_voice_clone(...):
    voice = await create_voice(...)
    voices_cache.clear()  # 전체 캐시 클리어 (단일 키만 있으므로)
    return voice
```

**장점**: 구현 간단
**단점**: 단일 인스턴스만

---

### Option B: Redis + 수동 무효화 ⭐ 추천

**구현**:
```python
import aioredis
from json import dumps, loads

redis_client = await aioredis.from_url("redis://redis:6379")

CACHE_KEY_VOICES = "tts:voices"
CACHE_TTL_VOICES = 3600

async def get_voices():
    cached = await redis_client.get(CACHE_KEY_VOICES)
    if cached:
        return loads(cached)
    
    voices = await elevenlabs_api.get_voices()
    await redis_client.setex(
        CACHE_KEY_VOICES, 
        CACHE_TTL_VOICES, 
        dumps(voices)
    )
    return voices

async def create_voice_clone(...):
    voice = await elevenlabs_api.create_voice(...)
    # 즉시 무효화
    await redis_client.delete(CACHE_KEY_VOICES)
    return voice
```

**장점**: 분산 캐싱, 확장성
**단점**: Redis 인프라 필요

---

### Option C: Redis + 태그 기반

**구현**:
```python
# 태그를 Set으로 관리
CACHE_TAG_VOICES = "cache:tag:voices"

async def get_voices():
    cached = await redis_client.get(CACHE_KEY_VOICES)
    if cached:
        return loads(cached)
    
    voices = await elevenlabs_api.get_voices()
    await redis_client.setex(CACHE_KEY_VOICES, CACHE_TTL_VOICES, dumps(voices))
    # 태그에 키 추가
    await redis_client.sadd(CACHE_TAG_VOICES, CACHE_KEY_VOICES)
    return voices

async def create_voice_clone(...):
    voice = await elevenlabs_api.create_voice(...)
    # 태그로 모든 관련 캐시 무효화
    keys = await redis_client.smembers(CACHE_TAG_VOICES)
    if keys:
        await redis_client.delete(*keys)
    await redis_client.delete(CACHE_TAG_VOICES)
    return voice
```

**장점**: 유연한 무효화
**단점**: 구현 복잡도 증가

---

## 🎯 최종 추천: Redis + Write-Invalidate + TTL

### 구현 전략

1. **기본 캐싱**: TTL 1시간으로 자동 만료
2. **즉시 무효화**: Voice 생성/수정/삭제 시 즉시 캐시 삭제
3. **안전장치**: TTL로 최대 1시간 후 자동 갱신

### 예상 동작

**시나리오 1: 정상 조회**
1. 사용자 A가 `/voices` 호출
2. 캐시 미스 → ElevenLabs API 호출
3. 결과를 캐시에 저장 (TTL 1시간)
4. 사용자 B가 `/voices` 호출
5. 캐시 히트 → 즉시 반환 ✅

**시나리오 2: Voice 생성 후 조회**
1. 사용자 A가 `/voices` 호출 → 캐시 저장
2. 사용자 B가 Voice Clone 생성
3. **캐시 무효화** (`cache.delete("tts:voices")`)
4. 사용자 C가 `/voices` 호출
5. 캐시 미스 → ElevenLabs API 호출 (새 음성 포함)
6. 새 결과를 캐시에 저장 ✅

**시나리오 3: TTL 만료**
1. 캐시가 1시간 이상 유지
2. TTL 만료로 자동 삭제
3. 다음 조회 시 자동 갱신 ✅

---

## 📊 예상 효과 (무효화 포함)

### 캐시 히트율
- **무효화 없음**: 99% (거의 항상 캐시)
- **무효화 있음**: 95-98% (Voice 생성 시에만 갱신)

### 데이터 일관성
- **무효화 없음**: ❌ 오래된 데이터 노출
- **무효화 있음**: ✅ 최신 데이터 보장

### API 호출 감소
- **무효화 없음**: 99% 감소 (하지만 오래된 데이터)
- **무효화 있음**: 95-98% 감소 (최신 데이터 유지)

---

## ✅ 구현 체크리스트

### Phase 1: 기본 구현
- [ ] Redis 인프라 추가 (Docker Compose)
- [ ] 캐시 레이어 추상화 (`backend/core/cache.py`)
- [ ] TTS Voices 캐싱 구현
- [ ] TTL 설정 (1시간)

### Phase 2: 무효화 구현
- [ ] Voice 생성 엔드포인트 확인/구현
- [ ] Voice 생성 시 캐시 무효화 로직 추가
- [ ] Voice 삭제 시 캐시 무효화 로직 추가 (추후)
- [ ] Voice 수정 시 캐시 무효화 로직 추가 (추후)

### Phase 3: 테스트
- [ ] 캐시 히트 테스트
- [ ] 캐시 무효화 테스트
- [ ] TTL 만료 테스트
- [ ] 동시성 테스트 (여러 인스턴스)

---

## 💡 핵심 포인트

1. **TTL + Write-Invalidate**: 안전성과 정확성의 균형
2. **즉시 무효화**: Voice 생성 직후 캐시 삭제
3. **명시적 관리**: 모든 쓰기 작업에 무효화 로직 추가
4. **모니터링**: 캐시 히트율 추적으로 효과 확인

