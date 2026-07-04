"""
Speech-to-Text Service — transcribes interview answer recordings with
OpenAI's local Whisper model.

The model used to be loaded eagerly at import time. That meant any failure
(no internet on first run to download the "small" checkpoint, no ffmpeg on
PATH, etc.) crashed the entire backend at startup — taking down every other
endpoint (chat, dashboard, auth...) along with it, not just transcription.

It's now loaded lazily on first use (same pattern as evaluation_service's
BERT model), so the rest of the API stays up even if Whisper can't load,
and the real error is surfaced clearly instead of hiding behind a generic
"Could not transcribe your answer" on the frontend.
"""
import logging
import shutil
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None


class TranscriptionUnavailable(RuntimeError):
    """Raised when Whisper can't be loaded or a clip can't be transcribed."""


def _load_model():
    global _model
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:
            return _model

        if shutil.which("ffmpeg") is None:
            raise TranscriptionUnavailable(
                "ffmpeg is not installed / not on PATH. Whisper requires ffmpeg "
                "to decode audio. Install it (e.g. `apt install ffmpeg` on "
                "Ubuntu/Debian or `brew install ffmpeg` on macOS) and restart "
                "the backend."
            )

        try:
            import whisper 
            logger.info("Loading Whisper model ('small')...")
            _model = whisper.load_model("small")
            logger.info("Whisper model loaded.")
        except Exception as e:
            raise TranscriptionUnavailable(
                f"Failed to load the Whisper model: {e}"
            ) from e

        return _model


def preload() -> None:
    """Optionally warm the model up at startup. Never raises — logs and
    lets the rest of the API start normally if Whisper isn't ready yet."""
    try:
        _load_model()
    except TranscriptionUnavailable as e:
        logger.warning(str(e))


def speech_to_text(audio_path: str) -> str:
    """
    Converts an interviewee's recorded answer to text.
    Returns the transcribed text for evaluation.

    Raises TranscriptionUnavailable with a specific, actionable message on
    failure (missing ffmpeg, missing/corrupt/empty audio file, model load
    failure, etc.) instead of letting a raw exception bubble up as an opaque
    500.
    """
    import os

    if not audio_path or not os.path.isfile(audio_path):
        raise TranscriptionUnavailable(f"Audio file not found at '{audio_path}'.")

    if os.path.getsize(audio_path) == 0:
        raise TranscriptionUnavailable(
            "The uploaded recording was empty (0 bytes) — no audio was "
            "captured. Check microphone permissions and try again."
        )

    model = _load_model()

    try:
        result = model.transcribe(audio_path, language="en")
    except Exception as e:
        raise TranscriptionUnavailable(f"Whisper failed to transcribe the audio: {e}") from e

    text = (result.get("text") or "").strip()
    return text
