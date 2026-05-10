from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User
from app.schemas.schemas import UserOut, ProfileUpdateRequest, MessageResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_profile(
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the authenticated user's profile fields."""
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.job_title is not None:
        current_user.job_title = body.job_title
    if body.bio is not None:
        current_user.bio = body.bio
    db.add(current_user)
    return current_user


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete account by deactivating it."""
    current_user.is_active = False
    db.add(current_user)
    return {"message": "Account deactivated"}