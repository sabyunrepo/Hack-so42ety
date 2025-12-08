# ElevenLabs Voice 사용자별 관리 방법 분석

## 📋 요구사항

사용자별로 Voice를 등록하고 관리하여, 각 사용자에게 자신이 생성한 Voice만 반환하도록 구현

---

## 🔍 두 가지 접근 방식 비교

### Option A: 데이터베이스 저장 방식 (권장) ⭐⭐⭐⭐⭐

#### 구현 방식
1. **Voice 생성 시**: ElevenLabs API로 Voice 생성 → DB에 메타데이터 저장
2. **Voice 조회 시**: DB에서 `user_id`로 필터링하여 반환
3. **Voice 삭제 시**: ElevenLabs API 삭제 + DB 삭제

#### 장점 ✅

1. **완전한 제어권**
   - 사용자별 Voice 목록을 완전히 제어 가능
   - DB 쿼리로 빠른 필터링
   - 복잡한 검색/정렬 가능

2. **확장성**
   - 사용자별 통계 수집 용이
   - Voice 사용 이력 추적 가능
   - 권한 관리 (공유, 공개 등) 구현 가능

3. **안정성**
   - ElevenLabs API 장애 시에도 DB에서 목록 조회 가능
   - API 변경에 영향 적음
   - 데이터 일관성 보장

4. **성능**
   - DB 인덱싱으로 빠른 조회
   - 캐싱 전략 적용 용이 (`tts:voices:{user_id}`)
   - API 호출 최소화

5. **추가 기능 구현 용이**
   - Voice 태그, 카테고리 관리
   - Voice 사용 횟수 통계
   - Voice 공유 기능
   - Voice 즐겨찾기

#### 단점 ❌

1. **초기 구현 복잡도**
   - DB 모델 설계 필요
   - 마이그레이션 필요
   - 동기화 로직 필요 (ElevenLabs ↔ DB)

2. **데이터 동기화**
   - ElevenLabs에서 직접 삭제된 경우 동기화 필요
   - 주기적 동기화 작업 필요 (옵션)

3. **저장 공간**
   - DB에 메타데이터 저장 필요 (하지만 매우 작음)

#### 구현 예시

```python
# 1. DB 모델
class Voice(Base):
    __tablename__ = "voices"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    elevenlabs_voice_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(10))
    gender: Mapped[str] = mapped_column(String(20))
    preview_url: Mapped[Optional[str]] = mapped_column(String(1024))
    category: Mapped[str] = mapped_column(String(50))  # premade, cloned, custom
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 인덱스
    __table_args__ = (
        Index('idx_voice_user_id', 'user_id'),
        Index('idx_voice_user_active', 'user_id', 'is_active'),
    )

# 2. Voice 생성
async def create_voice_clone(
    self,
    user_id: uuid.UUID,
    name: str,
    audio_file: bytes,
) -> Dict[str, Any]:
    # ElevenLabs API로 Voice 생성
    tts_provider = self.ai_factory.get_tts_provider()
    elevenlabs_voice = await tts_provider.clone_voice(
        name=name,
        audio_file=audio_file
    )
    
    # DB에 저장
    voice = await self.voice_repo.create(
        user_id=user_id,
        elevenlabs_voice_id=elevenlabs_voice["voice_id"],
        name=elevenlabs_voice["name"],
        language=elevenlabs_voice.get("language", "en"),
        gender=elevenlabs_voice.get("gender", "unknown"),
        preview_url=elevenlabs_voice.get("preview_url"),
        category="cloned",
    )
    
    # 이벤트 발행 (캐시 무효화)
    await self.event_bus.publish(
        EventType.VOICE_CREATED,
        {"voice_id": str(voice.id), "user_id": str(user_id)}
    )
    
    return voice

# 3. Voice 조회 (사용자별)
@cache_result(key="tts:voices:{user_id}", ttl=3600)
async def get_voices(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
    # DB에서 사용자별 Voice 조회
    voices = await self.voice_repo.get_user_voices(user_id)
    
    # 기본 Voice (premade) 추가
    tts_provider = self.ai_factory.get_tts_provider()
    premade_voices = await tts_provider.get_available_voices()
    premade_voices = [
        v for v in premade_voices 
        if v.get("category") == "premade"
    ]
    
    # 사용자 Voice + 기본 Voice 합치기
    result = []
    for voice in voices:
        result.append({
            "voice_id": voice.elevenlabs_voice_id,
            "name": voice.name,
            "language": voice.language,
            "gender": voice.gender,
            "preview_url": voice.preview_url,
            "category": voice.category,
            "is_custom": True,
        })
    
    result.extend(premade_voices)
    return result

# 4. Voice 삭제
async def delete_voice(
    self,
    user_id: uuid.UUID,
    voice_id: uuid.UUID,
) -> bool:
    # DB에서 조회
    voice = await self.voice_repo.get(voice_id)
    if not voice or voice.user_id != user_id:
        raise VoiceNotFoundException(voice_id=str(voice_id))
    
    # ElevenLabs에서 삭제
    tts_provider = self.ai_factory.get_tts_provider()
    await tts_provider.delete_voice(voice.elevenlabs_voice_id)
    
    # DB에서 삭제
    await self.voice_repo.delete(voice_id)
    
    # 이벤트 발행
    await self.event_bus.publish(
        EventType.VOICE_DELETED,
        {"voice_id": str(voice_id), "user_id": str(user_id)}
    )
    
    return True
```

---

### Option B: ElevenLabs API 메타데이터 필터링 방식

#### 구현 방식
1. **Voice 생성 시**: ElevenLabs API로 Voice 생성 시 `description` 또는 `labels`에 `user_id` 포함
2. **Voice 조회 시**: ElevenLabs API에서 모든 Voice 가져온 후 `description`/`labels`에서 `user_id` 필터링
3. **Voice 삭제 시**: ElevenLabs API 삭제만 수행

#### 장점 ✅

1. **구현 단순성**
   - DB 모델 불필요
   - 마이그레이션 불필요
   - 단일 소스 (ElevenLabs API)

2. **데이터 일관성**
   - ElevenLabs가 단일 소스
   - 동기화 문제 없음

3. **저장 공간 절약**
   - DB 저장 불필요

#### 단점 ❌

1. **API 의존성**
   - ElevenLabs API 장애 시 Voice 목록 조회 불가
   - API 변경에 취약
   - Rate Limit 제약

2. **제한된 기능**
   - ElevenLabs API가 `description`/`labels`에 `user_id` 저장 지원 여부 불확실
   - 복잡한 검색/정렬 어려움
   - 통계 수집 어려움

3. **성능**
   - 매번 API 호출 필요
   - 필터링을 클라이언트에서 수행 (비효율)
   - 캐싱 전략 제한적

4. **확장성 제한**
   - 사용자별 통계 수집 어려움
   - 권한 관리 구현 어려움
   - Voice 공유 기능 구현 어려움

5. **보안**
   - `description`에 `user_id` 저장 시 노출 위험
   - 다른 사용자가 `description` 수정 가능 (ElevenLabs API 권한에 따라)

#### 구현 예시 (가정)

```python
# 1. Voice 생성 (description에 user_id 포함)
async def create_voice_clone(
    self,
    user_id: uuid.UUID,
    name: str,
    audio_file: bytes,
) -> Dict[str, Any]:
    tts_provider = self.ai_factory.get_tts_provider()
    
    # ElevenLabs API 호출 (description에 user_id 포함)
    # ⚠️ 주의: ElevenLabs API가 description 파라미터를 지원하는지 확인 필요
    voice = await tts_provider.clone_voice(
        name=name,
        audio_file=audio_file,
        description=f"user_id:{user_id}",  # 지원 여부 불확실
    )
    
    return voice

# 2. Voice 조회 (필터링)
@cache_result(key="tts:voices:{user_id}", ttl=3600)
async def get_voices(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
    # ElevenLabs API에서 모든 Voice 가져오기
    tts_provider = self.ai_factory.get_tts_provider()
    all_voices = await tts_provider.get_available_voices()
    
    # 클라이언트에서 필터링 (비효율)
    user_voices = []
    for voice in all_voices:
        description = voice.get("description", "")
        if f"user_id:{user_id}" in description:
            user_voices.append(voice)
    
    # 기본 Voice (premade) 추가
    premade_voices = [
        v for v in all_voices 
        if v.get("category") == "premade"
    ]
    
    return user_voices + premade_voices
```

#### ⚠️ 주의사항

1. **ElevenLabs API 지원 여부 불확실**
   - `description` 파라미터가 Voice 생성 시 지원되는지 확인 필요
   - `labels` 필드에 사용자 정보 저장 가능 여부 확인 필요
   - API 문서 확인 필요: https://elevenlabs.io/docs/api-reference/voices-add

2. **보안 문제**
   - `description`에 `user_id` 저장 시 다른 사용자에게 노출될 수 있음
   - ElevenLabs API 권한에 따라 다른 사용자가 수정 가능할 수 있음

3. **필터링 성능**
   - 모든 Voice를 가져온 후 클라이언트에서 필터링 (비효율)
   - Voice가 많아질수록 성능 저하

---

## 📊 상세 비교표

| 항목 | Option A: DB 저장 | Option B: API 메타데이터 |
|------|------------------|------------------------|
| **구현 복잡도** | 중간 (DB 모델 필요) | 낮음 (단순 필터링) |
| **확장성** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **성능** | ⭐⭐⭐⭐⭐ (DB 인덱싱) | ⭐⭐⭐ (API 호출) |
| **안정성** | ⭐⭐⭐⭐⭐ (DB 독립) | ⭐⭐ (API 의존) |
| **기능 확장** | ⭐⭐⭐⭐⭐ (통계, 권한 등) | ⭐⭐ (제한적) |
| **데이터 일관성** | ⭐⭐⭐⭐ (동기화 필요) | ⭐⭐⭐⭐⭐ (단일 소스) |
| **보안** | ⭐⭐⭐⭐⭐ (DB 권한 관리) | ⭐⭐⭐ (API 의존) |
| **유지보수** | ⭐⭐⭐⭐ (동기화 로직) | ⭐⭐⭐⭐⭐ (단순) |

---

## 🎯 최종 권장사항

### ✅ Option A: 데이터베이스 저장 방식 (강력 권장)

#### 이유

1. **확장성**: 향후 기능 확장 (통계, 권한, 공유 등) 용이
2. **성능**: DB 인덱싱으로 빠른 조회, 캐싱 전략 적용 용이
3. **안정성**: ElevenLabs API 장애 시에도 목록 조회 가능
4. **보안**: DB 레벨에서 권한 관리 가능
5. **업계 표준**: 대부분의 SaaS 서비스가 사용하는 방식

#### 구현 단계

1. **Phase 1: DB 모델 및 마이그레이션**
   - `Voice` 모델 생성
   - 마이그레이션 작성
   - Repository 생성

2. **Phase 2: Voice 생성 로직**
   - ElevenLabs API 호출
   - DB 저장
   - 이벤트 발행

3. **Phase 3: Voice 조회 로직**
   - 사용자별 필터링
   - 캐싱 적용
   - 기본 Voice (premade) 병합

4. **Phase 4: Voice 삭제 로직**
   - ElevenLabs API 삭제
   - DB 삭제
   - 이벤트 발행

5. **Phase 5: 동기화 로직 (옵션)**
   - 주기적 동기화 작업
   - ElevenLabs → DB 동기화

---

## 🔄 하이브리드 접근 방식 (고급)

### Option C: DB + API 동기화

#### 구현 방식
1. **Voice 생성**: ElevenLabs API → DB 저장
2. **Voice 조회**: DB에서 조회 (주), ElevenLabs API 동기화 (백그라운드)
3. **동기화**: 주기적으로 ElevenLabs API와 DB 동기화

#### 장점
- DB의 성능 + API의 최신성
- API 장애 시에도 DB에서 조회 가능
- 데이터 일관성 보장

#### 단점
- 구현 복잡도 높음
- 동기화 로직 필요

---

## 📝 구현 체크리스트

### Option A 구현 (권장)

- [ ] `Voice` 모델 생성
- [ ] 마이그레이션 작성
- [ ] `VoiceRepository` 생성
- [ ] `TTSService.create_voice_clone()` 수정 (DB 저장 추가)
- [ ] `TTSService.get_voices()` 수정 (사용자별 필터링)
- [ ] `TTSService.delete_voice()` 구현
- [ ] 캐시 키 변경: `tts:voices` → `tts:voices:{user_id}`
- [ ] 이벤트 핸들러 업데이트
- [ ] API 엔드포인트 수정 (`/voices` → `/voices?user_id=...` 또는 인증 기반)
- [ ] 테스트 작성

### Option B 구현 (비권장)

- [ ] ElevenLabs API `description` 파라미터 지원 확인
- [ ] `TTSService.create_voice_clone()` 수정 (description에 user_id 포함)
- [ ] `TTSService.get_voices()` 수정 (필터링 로직)
- [ ] 보안 검토 (user_id 노출 위험)
- [ ] 테스트 작성

---

## 🚀 다음 단계

1. **ElevenLabs API 문서 확인**
   - Voice 생성 API 파라미터 확인
   - `description` 또는 `labels` 지원 여부 확인

2. **Option A 구현 시작** (권장)
   - DB 모델 설계
   - 마이그레이션 작성
   - Repository 구현

3. **기존 Voice 마이그레이션** (필요 시)
   - 기존 ElevenLabs Voice를 DB로 마이그레이션
   - 사용자 매핑 로직

---

## 📚 참고 자료

- ElevenLabs API 문서: https://elevenlabs.io/docs/api-reference
- Voice Clone API: https://elevenlabs.io/docs/api-reference/voices-add
- Multi-tenant Architecture Best Practices

