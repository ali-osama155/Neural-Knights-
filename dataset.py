# -*- coding: utf-8 -*-
"""Dataset loader -- reads train/validation/test CSVs directly.

Expected columns: question, candidate_answer, expected_answer, score,
category, difficulty_level
"""

import pandas as pd
import torch
from torch.utils.data import Dataset


class InterviewDataset(Dataset):
    def __init__(self, csv_path, tokenizer, max_length=256):
        self.df = pd.read_csv(csv_path)
        required = {"question", "candidate_answer", "score"}
        missing = required - set(self.df.columns)
        if missing:
            raise ValueError(f"CSV {csv_path} is missing required columns: {missing}")
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        question = str(row["question"])
        answer = str(row["candidate_answer"])
        score = float(row["score"])

        encoding = self.tokenizer(
            question,
            answer,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        item = {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "score": torch.tensor(score, dtype=torch.float),
        }
        if "token_type_ids" in encoding:
            item["token_type_ids"] = encoding["token_type_ids"].squeeze(0)
        return item
