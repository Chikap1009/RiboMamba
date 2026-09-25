"""Build any of the three Phase 4 models from a run's config, and pick its training objective.

    arch          model                               objective
    transformer   TransformerDenoiser (Phase 2)       masked diffusion (diffusion_loss)
    bimamba       MambaModel(bidirectional=True)      masked diffusion (diffusion_loss)
    ar_mamba      MambaModel(bidirectional=False)     left to right (ar_loss)

Configs written before Phase 4 have no "arch" key: they are Transformers.
"""

import torch

from ribomamba.diffusion.masked import diffusion_loss
from ribomamba.models.transformer import TransformerConfig, TransformerDenoiser, count_parameters

ARCHS = ("transformer", "bimamba", "ar_mamba")
PARAMETER_TARGET = 14_174_976      # frozen protocol P4: every compared model within +-2 % of the Phase 2 baseline
PARAMETER_TOLERANCE = 0.02


def build_model(cfg: dict) -> torch.nn.Module:
    arch = cfg.get("arch", "transformer")
    if arch == "transformer":
        return TransformerDenoiser(TransformerConfig(d_model=cfg["d_model"], n_layers=cfg["n_layers"],
                                                     n_heads=cfg["n_heads"], dropout=cfg.get("dropout", 0.0)))
    if arch not in ARCHS:
        raise ValueError(f"unknown arch {arch!r}; expected one of {ARCHS}")
    from ribomamba.models.bimamba import MambaConfig, MambaModel    # imported only when needed (GPU kernels)
    return MambaModel(MambaConfig(d_model=cfg["d_model"], n_layers=cfg["n_layers"], d_state=cfg["d_state"],
                                  expand=cfg["expand"], headdim=cfg["headdim"], bidirectional=arch == "bimamba",
                                  dropout=cfg.get("dropout", 0.0)))


def objective(arch: str):
    """The training loss for an architecture: (model, ids, attention_mask, generator) -> (loss, stats)."""
    if arch == "ar_mamba":
        from ribomamba.autoregressive import ar_loss
        return ar_loss
    return diffusion_loss


def check_parameter_budget(model: torch.nn.Module) -> int:
    """Raise unless the model is within the protocol's +-2 % of the Transformer baseline; return its count."""
    n = count_parameters(model)
    if abs(n / PARAMETER_TARGET - 1) > PARAMETER_TOLERANCE:
        raise ValueError(f"{n:,} parameters is {100 * (n / PARAMETER_TARGET - 1):+.2f} % from the protocol's "
                         f"{PARAMETER_TARGET:,} (P4 allows +-{100 * PARAMETER_TOLERANCE:.0f} %)")
    return n
