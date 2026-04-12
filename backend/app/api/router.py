from fastapi import APIRouter
from app.api.v1 import proxy, voice, images, research, health, auth_history

api_router = APIRouter()

# Auth + History + Memory
api_router.include_router(auth_history.router, prefix="/v1", tags=["auth"])

# OpenAI-compatible proxy
api_router.include_router(proxy.router, prefix="/v1", tags=["proxy"])

# Voice pipeline (ASR + TTS)
api_router.include_router(voice.router, prefix="/v1/voice", tags=["voice"])

# Vision + image generation
api_router.include_router(images.router, prefix="/v1", tags=["images"])

# Deep Research
api_router.include_router(research.router, prefix="/v1", tags=["research"])

# Health checks
api_router.include_router(health.router, prefix="/v1", tags=["health"])
