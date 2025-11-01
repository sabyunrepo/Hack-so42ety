FROM python:3.12-alpine

WORKDIR /app

# wget, ffmpeg 설치 (헬스체크, 오디오 처리용)
RUN apk add --no-cache wget ffmpeg

# requirements.txt 복사 및 의존성 설치
COPY src/tts/requirements.txt /app/tts/requirements.txt
RUN pip install --no-cache-dir -r /app/tts/requirements.txt

# 소스 코드 복사 (Feature-First 구조)
COPY src/tts/main.py /app/tts/main.py
COPY src/tts/core /app/tts/core
COPY src/tts/shared /app/tts/shared
COPY src/tts/features /app/tts/features
COPY src/tts/src /app/tts/src
COPY src/tts/utils /app/tts/utils

# 작업 디렉토리 설정
WORKDIR /app/tts

# 포트 노출 (환경변수로 동적 설정)
EXPOSE ${TTS_API_PORT:-8000}

# FastAPI 앱 실행 (환경변수로 포트 및 리로드 옵션 제어)
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${TTS_API_PORT:-8000} ${UVICORN_RELOAD:+--reload}"
