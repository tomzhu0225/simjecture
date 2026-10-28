"""One-pass multi-field candidate scoring for scientific and general decisions."""

from __future__ import annotations

import time

from .decision_interface import encode_request
from .model import MonitorModel


class DecisionModel(MonitorModel):
    def encode(self, row):
        encoded = encode_request(row, self.tokenizer, maximum_tokens=self.max_tokens)
        torch = self.torch
        batch = dict(input_ids=torch.tensor([encoded["input_ids"]], device="cuda"))
        positions = torch.tensor(encoded["positions"], device="cuda")
        return batch, positions, encoded

    def forward_decisions(self, row):
        batch, positions, encoded = self.encode(row)
        logits = self.model(**batch, use_cache=False, logits_to_keep=positions).logits[0].float()
        return logits, encoded

    def predict(self, row):
        started = time.perf_counter()
        with self.torch.inference_mode():
            logits, encoded = self.forward_decisions(row)
            probabilities = {}
            for i, (field, labels) in enumerate(encoded["labels"].items()):
                values = logits[i, encoded["symbol_ids"][: len(labels)]] / self.temperature
                probabilities[field] = dict(
                    zip(labels, values.softmax(-1).cpu().tolist(), strict=True)
                )
        self.torch.cuda.synchronize()
        return dict(
            answers={field: max(values, key=values.get) for field, values in probabilities.items()},
            probabilities=probabilities,
            prompt_sha256=encoded["prompt_sha256"],
            input_tokens=len(encoded["input_ids"]),
            total_seconds=time.perf_counter() - started,
            model_identity=self.identity,
            temperature=self.temperature,
            calibration_note="Checkpoint scaling is not revalidated after adaptation.",
        )
