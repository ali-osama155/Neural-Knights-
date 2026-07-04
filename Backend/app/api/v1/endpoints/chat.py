from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, ChatMessage
from app.schemas.schemas import ChatMessageIn, ChatMessageOut, ChatResponse, MessageResponse
from app.services.ai_service import chat_with_ai

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatMessageIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message and receive an AI reply. Stores full conversation history."""
    # Load recent history for context
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(20)
    )
    history_records = list(reversed(history_result.scalars().all()))
    history = [{"role": m.role, "content": m.content} for m in history_records]

    # Save user message
    user_msg = ChatMessage(user_id=current_user.id, role="user", content=body.content)
    db.add(user_msg)
    await db.flush()

    # Get AI response
    ai_text = await chat_with_ai(history, body.content)

    ai_msg = ChatMessage(user_id=current_user.id, role="assistant", content=ai_text)
    db.add(ai_msg)
    await db.flush()

    return ChatResponse(
        user_message=ChatMessageOut.model_validate(user_msg),
        ai_message=ChatMessageOut.model_validate(ai_msg),
    )


@router.get("/history", response_model=list[ChatMessageOut])
async def get_chat_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return recent chat history for the current user."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    return result.scalars().all()


@router.delete("/history", response_model=MessageResponse)
async def clear_chat_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clear all chat messages for the current user."""
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.user_id == current_user.id)
    )
    for msg in result.scalars().all():
        await db.delete(msg)
    return {"message": "Chat history cleared"}