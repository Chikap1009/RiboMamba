"""Load a trained model from a checkpoint written by scripts/train.py.

One place, because sampling and evaluation both need it, and Phase 4 adds
backbones: the checkpoint's config says which architecture to rebuild
(ribomamba/models/build.py).
"""

import torch

from ribomamba.models.build import build_model


def load_model(checkpoint, weights: str = "ema", device="cuda") -> tuple[torch.nn.Module, dict]:
    """(model in eval mode on `device`, the raw checkpoint dict). weights: "ema" (default) or "live"."""
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model = build_model(state["config"])
    model.load_state_dict(state["ema" if weights == "ema" else "model"])
    return model.to(device).eval(), state
