"""Load a trained denoiser from a checkpoint written by scripts/train.py.

One place, because sampling and evaluation both need it, and Phase 4 adds
backbones: the checkpoint's config says which architecture to rebuild.
"""

import torch

from ribomamba.models.transformer import TransformerConfig, TransformerDenoiser


def load_model(checkpoint, weights: str = "ema", device="cuda") -> tuple[torch.nn.Module, dict]:
    """(model in eval mode on `device`, the raw checkpoint dict). weights: "ema" (default) or "live"."""
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    cfg = state["config"]
    model = TransformerDenoiser(TransformerConfig(d_model=cfg["d_model"], n_layers=cfg["n_layers"],
                                                  n_heads=cfg["n_heads"]))
    model.load_state_dict(state["ema" if weights == "ema" else "model"])
    return model.to(device).eval(), state
