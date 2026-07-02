# -*- coding: utf-8 -*-
"""Trains InterviewScorer on train.csv, validates on validation.csv each epoch,
saves the best checkpoint by val_MAE."""

import os
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

from model import InterviewScorer
from dataset import InterviewDataset

MODEL_NAME = "bert-base-uncased"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
SAVE_DIR = os.path.join(os.path.dirname(__file__), "saved_model")
EPOCHS = 4
BATCH_SIZE = 16
LR = 2e-5
MAX_LENGTH = 256


def evaluate(model, loader, device, criterion):
    model.eval()
    total_loss = 0.0
    total_abs_err = 0.0
    total_sq_err = 0.0
    n = 0
    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            token_type_ids = batch.get("token_type_ids")
            if token_type_ids is not None:
                token_type_ids = token_type_ids.to(device)
            scores = batch["score"].to(device)

            preds = model(input_ids, attention_mask, token_type_ids)
            loss = criterion(preds, scores)

            total_loss += loss.item() * len(scores)
            total_abs_err += torch.sum(torch.abs(preds - scores)).item()
            total_sq_err += torch.sum((preds - scores) ** 2).item()
            n += len(scores)

    val_loss = total_loss / n
    val_mae = total_abs_err / n
    val_rmse = (total_sq_err / n) ** 0.5
    return val_loss, val_mae, val_rmse


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    os.makedirs(SAVE_DIR, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = InterviewScorer(MODEL_NAME).to(device)

    train_ds = InterviewDataset(os.path.join(DATA_DIR, "train.csv"), tokenizer, MAX_LENGTH)
    val_ds = InterviewDataset(os.path.join(DATA_DIR, "validation.csv"), tokenizer, MAX_LENGTH)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR)
    criterion = nn.MSELoss()

    n_steps = len(train_loader)
    best_val_mae = float("inf")

    for epoch in range(1, EPOCHS + 1):
        model.train()
        start = time.time()
        running_loss = 0.0
        for step, batch in enumerate(train_loader, start=1):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            token_type_ids = batch.get("token_type_ids")
            if token_type_ids is not None:
                token_type_ids = token_type_ids.to(device)
            scores = batch["score"].to(device)

            optimizer.zero_grad()
            preds = model(input_ids, attention_mask, token_type_ids)
            loss = criterion(preds, scores)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            if step % 50 == 0:
                print(f"  epoch {epoch} step {step}/{n_steps} loss={loss.item():.4f}")

        train_loss = running_loss / n_steps
        val_loss, val_mae, val_rmse = evaluate(model, val_loader, device, criterion)
        elapsed = time.time() - start
        print(
            f"Epoch {epoch}/{EPOCHS} | train_loss={train_loss:.4f} | "
            f"val_loss={val_loss:.4f} | val_MAE={val_mae:.4f} | "
            f"val_RMSE={val_rmse:.4f} | {elapsed:.1f}s"
        )

        if val_mae < best_val_mae:
            best_val_mae = val_mae
            ckpt_path = os.path.join(SAVE_DIR, "best_model.pt")
            torch.save(model.state_dict(), ckpt_path)
            print(f"  -> New best model saved (val_MAE={val_mae:.4f}) to {ckpt_path}")

    print(f"\nTraining complete. Best val MAE: {best_val_mae:.4f}")
    print(f"Best checkpoint: {os.path.join(SAVE_DIR, 'best_model.pt')}")


if __name__ == "__main__":
    main()
