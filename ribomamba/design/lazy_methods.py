"""Model-based harness methods, registered WITHOUT importing torch.

Worker processes that run only CPU methods must not import torch: its CUDA build costs ~1 GB of
host memory per process (the final benchmark nearly exhausted RAM with 10 workers). The settings
live here (single source of truth, imported by neural.py and tcd.py); the functions are loaded on
first call.
"""

import importlib

NEURAL_SETTINGS = {"checkpoint": "checkpoints/tf_M_do0/best.pt", "weights": "ema", "temperature": 1.0,
                   "decoding": "sequential chain rule, one position per forward pass, legal-move restricted"}
TCD_CHECKPOINT = "checkpoints/tcd_v1/tcd.pt"
TCD_SETTINGS = {"checkpoint": TCD_CHECKPOINT, "steps": 32, "batch": 32, "temperature": 1.0,
                "pair_rule": "product of conditional marginals restricted to canonical pairs"}


def _lazy(module: str, name: str):
    def call(*args, **kwargs):
        return getattr(importlib.import_module(module), name)(*args, **kwargs)
    call.__name__ = name
    return call


LAZY_METHODS = {
    "neural_feedback_edits": _lazy("ribomamba.design.neural", "neural_feedback_edits"),
    "neural_random_edits": _lazy("ribomamba.design.neural", "neural_random_edits"),
    "tcd_sample": _lazy("ribomamba.design.tcd", "tcd_sample"),
    "uncond_sample": _lazy("ribomamba.design.tcd", "uncond_sample"),
}
LAZY_SETTINGS = {
    "neural_feedback_edits": dict(NEURAL_SETTINGS),
    "neural_random_edits": dict(NEURAL_SETTINGS),
    "tcd_sample": TCD_SETTINGS,
    "uncond_sample": {**TCD_SETTINGS, "checkpoint": "base"},
}
