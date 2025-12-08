from fastapi import APIRouter
from backend.api.v1.endpoints import auth, storybook, tts, user, metrics, files

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(storybook.router, prefix="/storybook", tags=["Storybook"])
api_router.include_router(tts.router, prefix="/tts", tags=["TTS"])
api_router.include_router(user.router, prefix="/user", tags=["User"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
api_router.include_router(files.router, tags=["Files"])
