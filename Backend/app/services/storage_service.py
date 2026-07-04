"""
Storage Service — saves interview video recordings.
Local disk by default; swap save_video() body for S3 when ready.
"""
from datetime import datetime, timezone
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from app.core.config import get_settings

settings = get_settings()
VIDEO_DIR = Path(settings.UPLOAD_DIR) / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)


async def save_video(file: UploadFile, user_id: int, session_id: int) -> str:
    """Save video file and return its path."""
    max_bytes = 500 * 1024 * 1024  # 500 MB cap for ~10 min video
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Video file is too large (500 MB max)",
        )

    ext = Path(file.filename).suffix.lower() or ".webm"
    filename = f"interview_{user_id}_{session_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{ext}"
    dest = VIDEO_DIR / filename
    dest.write_bytes(content)
    return str(dest)

    # ── S3 example (uncomment when ready) ────────────────────────
    # import boto3
    # s3 = boto3.client("s3")
    # key = f"interviews/{filename}"
    # s3.put_object(Bucket="your-bucket", Key=key, Body=content)
    # return f"s3://your-bucket/{key}"