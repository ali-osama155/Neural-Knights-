# -*- coding: utf-8 -*-
"""
Evaluation Service — Answer scoring using Sarah's fine-tuned BERT model.

Role in the pipeline:
    Ali (CV + skills JSON)
        -> Reem (generate-questions)
        -> Reem (text-to-speech question / speech-to-text answer)
        -> THIS MODULE (score the transcribed answer, 0-10)
        -> Mariam's API / frontend (final score + feedback)

Model details (as trained by Sarah, not retrained here):
    base model   : bert-base-uncased
    task         : regression, 0-10 answer-quality score
    MAE ~0.486 / RMSE ~0.645 / Pearson ~0.978 on the held-out test set

This service only performs inference. Training code (train.py / dataset.py /
evaluate.py) is intentionally not part of the backend — the checkpoint
(`best_model.pt`) is used as-is.
"""
import logging
import os
import threading
from typing import Optional

import torch
from fastapi.concurrency import run_in_threadpool
from transformers import AutoTokenizer

from app.core.config import get_settings
from app.ml.model import InterviewScorer

logger = logging.getLogger(__name__)
settings = get_settings()

_lock = threading.Lock()
_device: Optional[torch.device] = None
_model: Optional[InterviewScorer] = None
_tokenizer = None


class EvaluationModelUnavailable(RuntimeError):
    """Raised when the checkpoint is missing or fails to load."""


def _checkpoint_path() -> str:
    return os.path.join(settings.EVAL_MODEL_DIR, "best_model.pt")


def is_ready() -> bool:
    """True if the model is already loaded in memory."""
    return _model is not None


def _load() -> None:
    """Load tokenizer + model weights into memory exactly once (thread-safe)."""
    global _device, _model, _tokenizer
    if _model is not None:
        return
    with _lock:
        if _model is not None:  # re-check inside the lock (another thread may have loaded it)
            return

        ckpt_path = _checkpoint_path()
        if not os.path.isfile(ckpt_path):
            raise EvaluationModelUnavailable(
                f"Evaluation model checkpoint not found at '{ckpt_path}'. "
                "Copy best_model.pt into app/ml/saved_model/ "
                "(see app/ml/saved_model/README.md)."
            )

        logger.info("Loading answer-evaluation model '%s'...", settings.EVAL_MODEL_NAME)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = AutoTokenizer.from_pretrained(settings.EVAL_MODEL_NAME)
        model = InterviewScorer(settings.EVAL_MODEL_NAME).to(device)

        try:
            state_dict = torch.load(ckpt_path, map_location=device)
            model.load_state_dict(state_dict)
        except Exception as e:
            raise EvaluationModelUnavailable(
                f"Failed to load evaluation checkpoint at '{ckpt_path}': {e}"
            ) from e

        model.eval()

        _device, _tokenizer, _model = device, tokenizer, model
        logger.info("Evaluation model ready on device=%s", device)


def preload() -> None:
    """
    Call once at app startup (see app/main.py lifespan) to warm the model up
    before the first real request — avoids a slow first call during the demo.
    Never raises: if the checkpoint isn't in place yet, logs a warning and
    lets the rest of the API start normally.
    """
    try:
        _load()
    except EvaluationModelUnavailable as e:
        logger.warning(str(e))


def _score_sync(question: str, candidate_answer: str) -> float:
    _load()
    encoding = _tokenizer(
        question,
        candidate_answer,
        truncation=True,
        max_length=settings.EVAL_MAX_LENGTH,
        padding="max_length",
        return_tensors="pt",
    )
    input_ids = encoding["input_ids"].to(_device)
    attention_mask = encoding["attention_mask"].to(_device)
    token_type_ids = encoding.get("token_type_ids")
    if token_type_ids is not None:
        token_type_ids = token_type_ids.to(_device)

    with torch.no_grad():
        pred = _model(input_ids, attention_mask, token_type_ids)

    score = float(pred.item())
    return max(0.0, min(10.0, score))  # clamp to the valid 0-10 range


async def score_answer(question: str, candidate_answer: str) -> float:
    """
    Score a single (question, candidate_answer) pair.

    BERT inference is blocking (CPU/GPU-bound), so it runs in a worker
    thread to avoid blocking the FastAPI event loop while other requests
    (e.g. speech-to-text, question generation) are in flight.

    Raises EvaluationModelUnavailable if the checkpoint isn't loaded.
    """
    if not candidate_answer or not candidate_answer.strip():
        # No transcribed speech (e.g. candidate stayed silent / STT failed) —
        # score as 0 without spending a model call on it.
        return 0.0
    return await run_in_threadpool(_score_sync, question, candidate_answer)


def score_label(score: float) -> str:
    """Simple qualitative bucket for a numeric score (used as `feedback`)."""
    if score >= 8.5:
        return "Excellent answer"
    if score >= 7:
        return "Strong answer"
    if score >= 5:
        return "Adequate answer"
    if score >= 3:
        return "Weak answer"
    return "Very weak / off-topic answer"
