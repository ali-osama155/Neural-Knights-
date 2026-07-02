# -*- coding: utf-8 -*-
"""Evaluates the best checkpoint on test.csv: overall metrics, per-category MAE,
example predictions, and worst predictions (for manual quality inspection)."""

import os
import torch
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

from model import InterviewScorer
from dataset import InterviewDataset

MODEL_NAME = "bert-base-uncased"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
SAVE_DIR = os.path.join(os.path.dirname(__file__), "saved_model")
BATCH_SIZE = 16
MAX_LENGTH = 256


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = InterviewScorer(MODEL_NAME).to(device)
    ckpt_path = os.path.join(SAVE_DIR, "best_model.pt")
    model.load_state_dict(torch.load(ckpt_path, map_location=device))
    model.eval()

    test_csv = os.path.join(DATA_DIR, "test.csv")
    test_ds = InterviewDataset(test_csv, tokenizer, MAX_LENGTH)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    all_preds, all_true = [], []
    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            token_type_ids = batch.get("token_type_ids")
            if token_type_ids is not None:
                token_type_ids = token_type_ids.to(device)
            scores = batch["score"]

            preds = model(input_ids, attention_mask, token_type_ids).cpu().numpy()
            all_preds.extend(preds.tolist())
            all_true.extend(scores.numpy().tolist())

    df = pd.read_csv(test_csv)
    df["predicted"] = all_preds
    df["true_score"] = all_true
    df["abs_error"] = (df["predicted"] - df["true_score"]).abs()

    mae = df["abs_error"].mean()
    rmse = np.sqrt(((df["predicted"] - df["true_score"]) ** 2).mean())
    pearson = np.corrcoef(df["predicted"], df["true_score"])[0, 1]

    print("\n=== Overall Metrics ===")
    print(f"MAE:  {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"Pearson correlation (pred vs true): {pearson:.4f}")

    print("\n=== Per-Category MAE ===")
    for cat, group in df.groupby("category"):
        print(f"  {cat:<30} MAE={group['abs_error'].mean():.4f}  (n={len(group)})")

    print("\n=== 10 Example Predictions ===")
    for _, row in df.sample(min(10, len(df)), random_state=0).iterrows():
        print(f"\nQ: {row['question']}")
        print(f"A: {row['candidate_answer'][:150]}...")
        print(f"True score: {row['true_score']:.1f} | Predicted: {row['predicted']:.1f}")

    print("\n=== 10 Worst Predictions (largest |error|) ===")
    worst = df.sort_values("abs_error", ascending=False).head(10)
    for _, row in worst.iterrows():
        print(f"\nQ: {row['question']}")
        print(f"A: {row['candidate_answer'][:150]}...")
        print(f"True: {row['true_score']:.1f} | Predicted: {row['predicted']:.1f} | Error: {row['predicted']-row['true_score']:+.1f}")


if __name__ == "__main__":
    main()
