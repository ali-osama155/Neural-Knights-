# -*- coding: utf-8 -*-
"""Simple inference utility: score a single (question, candidate_answer) pair."""

import os
import torch
from transformers import AutoTokenizer

from model import InterviewScorer

MODEL_NAME = "bert-base-uncased"
SAVE_DIR = os.path.join(os.path.dirname(__file__), "saved_model")
MAX_LENGTH = 256

_device = None
_model = None
_tokenizer = None


def _load():
    global _device, _model, _tokenizer
    if _model is not None:
        return
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    _model = InterviewScorer(MODEL_NAME).to(_device)
    ckpt_path = os.path.join(SAVE_DIR, "best_model.pt")
    _model.load_state_dict(torch.load(ckpt_path, map_location=_device))
    _model.eval()


def score_answer(question: str, candidate_answer: str) -> float:
    """Returns a predicted score in roughly the 0-10 range."""
    _load()
    encoding = _tokenizer(
        question,
        candidate_answer,
        truncation=True,
        max_length=MAX_LENGTH,
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
    return float(pred.item())


if __name__ == "__main__":
    q = "What is the difference between supervised and unsupervised learning?"
    a = "Supervised learning uses labeled data to train a model to predict outputs, while unsupervised learning finds patterns in unlabeled data."
    print(f"Predicted score: {score_answer(q, a):.2f}")
