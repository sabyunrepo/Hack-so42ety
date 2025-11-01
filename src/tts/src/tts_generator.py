"""
TTS Generator with ElevenLabs API
비동기 배치 처리 및 중첩 리스트 구조 보존
"""

import os
import uuid
import asyncio
import logging
import pprint
from pathlib import Path
from typing import List, Optional, Tuple
from dotenv import load_dotenv
from elevenlabs import ElevenLabs
from utils.audio_processor import AudioProcessor


# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)


class TtsGenerator:
    """ElevenLabs TTS 비동기 생성기 (싱글톤)"""

    _instance: Optional["TtsGenerator"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """TTS Generator 초기화"""
        # 중복 초기화 방지
        if hasattr(self, "_initialized"):
            return

        # ElevenLabs API 키 로드
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError(
                "ELEVENLABS_API_KEY가 설정되지 않았습니다. " ".env 파일을 확인하세요."
            )

        # ElevenLabs 클라이언트 초기화
        self.client = ElevenLabs(api_key=api_key)

        # 설정 로드
        self.output_dir = Path(os.getenv("TTS_OUTPUT_DIR", "/app/data/sound"))
        self.max_concurrent = int(os.getenv("TTS_MAX_CONCURRENT_REQUESTS", "5"))

        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 임시 디렉토리 생성 (클론 보이스용)
        self.temp_dir = self.output_dir / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # 세마포어 (동시 요청 제한)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

        # 클론 보이스 설정 (환경변수)
        self.CLONE_MIN_DURATION = int(os.getenv("CLONE_MIN_DURATION", "150"))
        self.CLONE_MAX_DURATION = int(os.getenv("CLONE_MAX_DURATION", "180"))
        self.CLONE_TARGET_DURATION = int(os.getenv("CLONE_TARGET_DURATION", "179"))

        # 오디오 프로세서
        self.audio_processor = AudioProcessor()

        self._initialized = True
        logger.info(
            f"TtsGenerator 초기화 완료 - "
            f"출력 경로: {self.output_dir}, "
            f"최대 동시 요청: {self.max_concurrent}"
        )

    async def generate_batch(
        self,
        texts: List[List[str]],
        voice_id: str = "TxWD6rImY3v4izkm2VL0",
        model_id: str = "eleven_v3",
        language: str = "en",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
    ) -> dict:
        """
        중첩 리스트 배치 TTS 생성

        Args:
            texts: 중첩 문자열 리스트 (예: [["hello", "this"], ["is"], ["me", "too"]])
            voice_id: ElevenLabs 음성 ID
            model_id: TTS 모델 ID
            language: 언어 코드 (ISO 639-1)
            stability: 안정성 (0.0-1.0)
            similarity_boost: 유사도 부스트 (0.0-1.0)
            style: 스타일 강조 (0.0-1.0)

        Returns:
            dict: {"batch_id": str, "paths": List[List[str]]}
        """
        # 배치 요청 UUID 생성 및 폴더 생성
        batch_uuid = str(uuid.uuid4())
        batch_dir = self.output_dir / batch_uuid
        batch_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"배치 TTS 생성 시작 - "
            f"batch_id: {batch_uuid}, "
            f"voice_id: {voice_id}, "
            f"model: {model_id}"
        )

        # 1. 평탄화: 중첩 리스트를 1차원으로 변환하면서 구조 정보 저장
        flat_texts = []
        structure = []  # 각 그룹의 길이 저장

        for group in texts:
            structure.append(len(group))
            flat_texts.extend(group)

        logger.info(f"총 {len(flat_texts)}개 텍스트 처리 시작 (구조: {structure})")

        # 2. 모든 텍스트를 병렬로 처리
        tasks = [
            self._generate_single(
                text=text,
                batch_dir=batch_dir,
                voice_id=voice_id,
                model_id=model_id,
                language=language,
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
            )
            for text in flat_texts
        ]

        # 병렬 실행 (일부 실패 허용)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 에러 처리 및 경로 추출
        flat_paths = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"텍스트 '{flat_texts[idx]}' 처리 실패: {result}")
                flat_paths.append(None)  # 실패 시 None
            else:
                flat_paths.append(result)

        # 4. 재구조화: 원래 중첩 구조로 복원
        nested_paths = []
        start_idx = 0

        for group_size in structure:
            group_paths = flat_paths[start_idx : start_idx + group_size]
            nested_paths.append(group_paths)
            start_idx += group_size

        # 성공/실패 통계
        success_count = sum(1 for p in flat_paths if p is not None)
        logger.info(
            f"배치 TTS 생성 완료 - "
            f"batch_id: {batch_uuid}, "
            f"성공: {success_count}/{len(flat_paths)}"
        )

        return {"batch_id": batch_uuid, "paths": nested_paths}

    async def _generate_single(
        self,
        text: str,
        batch_dir: Path,
        voice_id: str = "TxWD6rImY3v4izkm2VL0",
        model_id: str = "eleven_v3",
        language: str = "en",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
    ) -> str:
        """
        단일 텍스트 TTS 생성 (text_to_dialogue 방식)

        Args:
            text: 변환할 텍스트
            voice_id: ElevenLabs 음성 ID
            model_id: TTS 모델 ID
            language: 언어 코드
            stability: 안정성
            similarity_boost: 유사도 부스트
            style: 스타일 강조

        Returns:
            생성된 MP3 파일 경로 (예: "/data/sound/uuid.mp3")

        Raises:
            Exception: TTS 생성 실패 시
        """
        # 세마포어로 동시 요청 수 제한
        async with self.semaphore:
            try:
                logger.debug(f"TTS 생성 시작: '{text[:30]}...'")

                # ElevenLabs API 호출 (text_to_dialogue 방식)
                loop = asyncio.get_event_loop()

                # 감정 디렉션 자동 추가 (없는 경우)
                if not text.strip().startswith("["):
                    text = f"[reading like a children's storybook] {text}"

                # text_to_dialogue 입력 형식으로 변환
                dialogue_inputs = [
                    {
                        "text": text,
                        "voice_id": voice_id,
                    }
                ]

                # 음성 설정 (settings 파라미터)
                voice_settings = {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style,
                }

                # text_to_dialogue.convert() 호출 (Iterator[bytes] 반환)
                audio_iterator = await loop.run_in_executor(
                    None,
                    lambda: self.client.text_to_dialogue.convert(
                        inputs=dialogue_inputs,
                        model_id=model_id,
                        language_code=language,
                        settings=voice_settings,
                    ),
                )

                # Iterator를 bytes로 변환
                audio_chunks = []
                for chunk in audio_iterator:
                    audio_chunks.append(chunk)

                decoded_audio = b"".join(audio_chunks)

                if not decoded_audio:
                    raise ValueError("오디오 데이터가 비어있습니다.")

                # UUID 생성 및 파일 경로 (배치 폴더 내)
                file_uuid = str(uuid.uuid4())
                file_path = batch_dir / f"{file_uuid}.mp3"

                # 파일 저장 (비동기)
                await self._save_audio_file(file_path, decoded_audio)

                logger.debug(f"TTS 생성 완료: {file_path}")

                # 컨테이너 내 절대 경로 반환 (/app 제거)
                return str(file_path).removeprefix("/app")

            except Exception as e:
                logger.error(f"TTS 생성 실패 ('{text[:30]}...'): {e}")
                raise

    async def _save_audio_file(self, file_path: Path, audio_data: bytes) -> None:
        """
        오디오 파일 비동기 저장

        Args:
            file_path: 저장할 파일 경로
            audio_data: 오디오 바이트 데이터
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: file_path.write_bytes(audio_data))

    async def generate_word(
        self,
        word: str,
        voice_id: str,
        output_path: Optional[str] = None,
        model_id: Optional[str] = "eleven_multilingual_v2",
        language: Optional[str] = "en",
        stability: Optional[float] = 0.5,
        similarity_boost: Optional[float] = 0.75,
        style: Optional[float] = 0.0,
    ) -> str:
        """
        단어 단위 TTS 생성 (Book별 voice_id 지원, text_to_dialogue 방식)

        Args:
            word: 변환할 단어
            voice_id: ElevenLabs 음성 ID (필수)
            output_path: 저장 경로 (Optional, 지정하지 않으면 기본 경로 사용)
            model_id: TTS 모델 ID
            language: 언어 코드
            stability: 안정성
            similarity_boost: 유사도 부스트
            style: 스타일 강조

        Returns:
            생성된 MP3 파일 경로 (예: "/data/sound/word/{book_id}/hello.mp3")

        Raises:
            Exception: TTS 생성 실패 시
        """
        # 출력 경로 설정
        if output_path:
            file_path = Path(output_path)
        else:
            # 기본 경로 (레거시 지원)
            word_dir = self.output_dir / "word"
            word_dir.mkdir(parents=True, exist_ok=True)
            file_path = word_dir / f"{word}.mp3"

        # 이미 파일이 존재하면 재사용 (캐싱)
        if file_path.exists():
            logger.info(f"캐시된 파일 재사용: {file_path}")
            return str(file_path).removeprefix("/app")

        # 환경변수 기본값 처리 (voice_id는 이제 필수이므로 제거)
        model_id = model_id or "eleven_multilingual_v2"
        language = language or os.getenv("TTS_DEFAULT_LANGUAGE", "en")
        stability = (
            stability
            if stability is not None
            else float(os.getenv("TTS_DEFAULT_STABILITY", "0.5"))
        )
        similarity_boost = (
            similarity_boost
            if similarity_boost is not None
            else float(os.getenv("TTS_DEFAULT_SIMILARITY_BOOST", "0.75"))
        )
        style = (
            style if style is not None else float(os.getenv("TTS_DEFAULT_STYLE", "0.0"))
        )

        logger.info(
            f"새 단어 TTS 생성: word={word}, voice_id={voice_id}, "
            f"model={model_id}, output={file_path}"
        )

        try:
            # ElevenLabs API 호출 (text_to_dialogue 방식)
            loop = asyncio.get_event_loop()

            # text_to_dialogue.convert() 호출 (Iterator[bytes] 반환)
            audio_iterator = await loop.run_in_executor(
                None,
                lambda: self.client.text_to_speech.convert(
                    text=word,
                    voice_id=voice_id,
                    model_id=model_id,
                    language_code=language,
                ),
            )

            # Iterator를 bytes로 변환
            audio_chunks = []
            for chunk in audio_iterator:
                audio_chunks.append(chunk)

            decoded_audio = b"".join(audio_chunks)

            if not decoded_audio:
                raise ValueError("오디오 데이터가 비어있습니다.")

            # 파일 저장
            await self._save_audio_file(file_path, decoded_audio)

            logger.info(f"단어 TTS 생성 완료: {file_path}")
            return str(file_path).removeprefix("/app")

        except Exception as e:
            logger.error(f"단어 TTS 생성 실패 ('{word}'): {e}")
            raise

    def get_stats(self) -> dict:
        """
        TTS Generator 통계 정보 반환

        Returns:
            dict: 설정 및 통계 정보
        """
        return {
            "output_dir": str(self.output_dir),
            "max_concurrent_requests": self.max_concurrent,
            "output_dir_exists": self.output_dir.exists(),
            "file_count": (
                len(list(self.output_dir.glob("*.mp3")))
                if self.output_dir.exists()
                else 0
            ),
        }

    async def get_clone_voice_list(self):
        """
        클론 보이스 목록 조회

        Returns:
            List[dict]: 보이스 목록 [{"voice_label": str, "voice_id": str}, ...]
        """
        # ElevenLabs API 호출 (동기 함수를 비동기로 실행)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: self.client.voices.get_all(show_legacy=False)
        )

        voices = []
        for x in response.voices:
            pprint.pprint(x)
            if x.category in "cloned":
                temp_data = {
                    "voice_label": x.name,
                    "voice_id": x.voice_id,
                    "description": x.description or "",
                    "category": (x.category if hasattr(x, "category") else "unknown"),
                    "preview_url": (
                        x.preview_url if hasattr(x, "preview_url") else "unknown"
                    ),
                    "labels": (x.labels if hasattr(x, "labels") and x.labels else {}),
                }
                # preview_url이 None이면 processing, 아니면 success
                if x.preview_url is None:
                    temp_data["state"] = "processing"
                else:
                    temp_data["state"] = "success"
                voices.append(temp_data)

        return voices

    # === Clone Voice Methods ===

    def validate_audio_duration_only(self, file_path: Path) -> float:
        """
        오디오 길이만 검증 (사전 검증용)

        Args:
            file_path: 오디오 파일 경로

        Returns:
            float: 오디오 길이 (초)

        Raises:
            ValueError: 길이 부족
        """
        return self.audio_processor.validate_duration(
            file_path, self.CLONE_MIN_DURATION
        )

    def _validate_and_process_audio(self, file_path: Path) -> Tuple[Path, float]:
        """
        오디오 길이 검증 및 처리 (트리밍 포함)

        Args:
            file_path: 오디오 파일 경로

        Returns:
            Tuple[Path, float]: (처리된 파일 경로, 최종 길이)

        Raises:
            ValueError: 길이 부족
        """
        # AudioProcessor로 길이 검증
        duration = self.audio_processor.validate_duration(
            file_path, self.CLONE_MIN_DURATION
        )

        # 3분 이상: 트리밍
        if duration >= self.CLONE_MAX_DURATION:
            logger.info(f"오디오 길이 {duration:.2f}초, 트리밍 시작")
            trimmed_path = self.audio_processor.trim_audio(
                file_path, self.CLONE_TARGET_DURATION
            )
            return trimmed_path, self.CLONE_TARGET_DURATION

        return file_path, duration

    def _cleanup_temp_file(self, file_path: Path) -> None:
        """임시 파일 삭제"""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"임시 파일 삭제: {file_path}")
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패: {e}")

    async def check_duplicate_voice_name(self, name: str) -> bool:
        """
        클론 보이스 이름 중복 확인

        Args:
            name: 확인할 이름

        Returns:
            bool: 중복 여부
        """
        voices = await self.get_clone_voice_list()
        return any(v["voice_label"] == name for v in voices)

    async def create_clone_voice(
        self, name: str, audio_file_path: Path, description: str = ""
    ) -> dict:
        """
        클론 보이스 생성 (메인 로직)

        Args:
            name: 보이스 이름
            audio_file_path: 오디오 파일 경로
            description: 보이스 설명

        Returns:
            dict: 생성된 보이스 정보

        Raises:
            ValueError: 검증 실패, API 오류
        """
        processed_path: Optional[Path] = None

        try:
            # 1. 오디오 길이 검증 및 처리
            processed_path, duration = self._validate_and_process_audio(audio_file_path)

            # 2. ElevenLabs API 호출 (동기 -> 비동기)
            loop = asyncio.get_event_loop()

            def create_voice():
                with open(processed_path, "rb") as f:
                    return self.client.voices.ivc.create(
                        name=name,
                        files=[f],
                        remove_background_noise=True,
                        description=description or None,
                    )

            response = await loop.run_in_executor(None, create_voice)

            logger.info(f"클론 보이스 생성 성공: {name} (ID: {response.voice_id})")

            # 3. 임시 파일 정리
            if processed_path != audio_file_path:
                self._cleanup_temp_file(processed_path)

            return {
                "voice_id": response.voice_id,
                "voice_label": name,
                "description": description,
                "category": "cloned",
                "duration": duration,
            }

        except ValueError:
            if processed_path and processed_path != audio_file_path:
                self._cleanup_temp_file(processed_path)
            raise

        except Exception as e:
            if processed_path and processed_path != audio_file_path:
                self._cleanup_temp_file(processed_path)

            error_msg = str(e)

            # ElevenLabs API 에러 처리
            if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                raise ValueError("클론 보이스 생성 한도에 도달했습니다.")
            elif "invalid" in error_msg.lower():
                raise ValueError("유효하지 않은 오디오 파일입니다.")
            elif "unauthorized" in error_msg.lower():
                raise ValueError("API 인증 실패. API 키를 확인하세요.")
            else:
                logger.error(f"클론 보이스 생성 실패: {error_msg}")
                raise ValueError(f"클론 보이스 생성 중 오류 발생: {error_msg}")
