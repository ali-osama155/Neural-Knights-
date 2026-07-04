# -*- coding: utf-8 -*-
"""BERT-based regression model for scoring interview answers 0-10.

Owner: Sarah (Answer Evaluation & Scoring).
This is an exact copy of the architecture used to train `best_model.pt`.
It must stay in sync with the training code — do not change layer shapes
or names here without retraining, or the checkpoint will fail to load.
"""
import torch
import torch.nn as nn
from transformers import AutoModel


class InterviewScorer(nn.Module):
    def __init__(self, model_name="bert-base-uncased", dropout=0.1):
        super().__init__()
        self.bert = AutoModel.from_pretrained(model_name)
        hidden_size = self.bert.config.hidden_size
        self.dropout = nn.Dropout(dropout)
        self.regressor = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 1),
        )

    def forward(self, input_ids, attention_mask, token_type_ids=None):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
        )
        # Use the pooled [CLS] representation
        pooled = outputs.last_hidden_state[:, 0, :]
        pooled = self.dropout(pooled)
        score = self.regressor(pooled).squeeze(-1)
        return score
