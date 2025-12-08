FROM python:3.12-alpine

WORKDIR /app

# wget 설치 (헬스체크용)
RUN apk add --no-cache wget

# requirements.txt 복사 및 의존성 설치
COPY src/storybook/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 포트 노출 (환경변수로 동적 설정)
EXPOSE ${STORYBOOK_API_PORT:-8001}

# FastAPI 앱 실행 (환경변수로 포트 및 리로드 옵션 제어)
CMD sh -c "uvicorn storybook.main:app --host 0.0.0.0 --port ${STORYBOOK_API_PORT:-8001} ${UVICORN_RELOAD:+--reload}"
