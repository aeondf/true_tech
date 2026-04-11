from fastapi import APIRouter
from app.api.v1 import proxy, tools, files, voice, images, memory, research, health

api_router = APIRouter()

# OpenAI-compatible proxy (OpenWebUI speaks to these)
api_router.include_router(proxy.router, prefix="/v1", tags=["proxy"])

# Tool endpoints
api_router.include_router(tools.router, prefix="/v1/tools", tags=["tools"])

# File handling
api_router.include_router(files.router, prefix="/v1/files", tags=["files"])

# Voice pipeline
api_router.include_router(voice.router, prefix="/v1/voice", tags=["voice"])

# Vision + image generation
api_router.include_router(images.router, prefix="/v1", tags=["images"])

# Memory CRUD
api_router.include_router(memory.router, prefix="/v1/memory", tags=["memory"])

# Deep Research
api_router.include_router(research.router, prefix="/v1", tags=["research"])

# Health checks
api_router.include_router(health.router, prefix="/v1", tags=["health"])
