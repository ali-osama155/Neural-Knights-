from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, cv, interviews, chat
from app.api.v1.endpoints import emotion

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(cv.router)
api_router.include_router(interviews.router)
api_router.include_router(chat.router)
api_router.include_router(emotion.router)