"""Masked discrete diffusion: forward masking, the training loss, and the sampler (Phase 2).

Continuous time t in (0, 1], linear schedule alpha_t = 1 - t, so at time t
each nucleotide is independently replaced by <mask> with probability t.
<mask> is absorbing: never un-masked in the forward process; once revealed in
the reverse process, a letter is never changed again.

Sequences are framed as  <bos> x_1 ... x_L <eos>  (D-010). The markers are
never masked and never scored: they tell the denoiser where the molecule
starts and ends. Without them, a fully masked input gives every position the
same vector, and a RoPE Transformer cannot tell positions apart at all
(measured: 2.11 bits/nt at t = 1 without markers vs 1.58 with, session 03).

Loss (negative ELBO, MDLM, Sahoo et al. 2024):
    E_t E_z [ (1/t) * sum over masked positions i of -log p_theta(x_i | z_t) ]
It is an upper bound on -log p_theta(x); divided by the number of
nucleotides and by ln 2 it becomes bits per nucleotide.
"""

import math

import torch
import torch.nn.functional as F

from ribomamba.data.tokenizer import BOS_ID, EOS_ID, MASK_ID, PAD_ID, is_nucleotide

T_MIN = 1e-3   # floor on t: the weight 1/t would explode as t -> 0 (and t = 0 masks nothing)


def sample_times(batch_size: int, device, generator: torch.Generator | None = None) -> torch.Tensor:
    """One t per sequence, spread evenly over [T_MIN, 1) ("low-discrepancy" sampling).

    t_i = (u + i / B) mod 1 with one random u: the batch covers the whole range
    of noise levels instead of clumping, which lowers the loss's variance.
    """
    u = torch.rand(1, device=device, generator=generator)
    t = (u + torch.arange(batch_size, device=device) / batch_size) % 1.0      # (B,) in [0, 1)
    return T_MIN + (1.0 - T_MIN) * t                                           # (B,) in [T_MIN, 1)


def mask_tokens(input_ids: torch.Tensor, t: torch.Tensor,
                generator: torch.Generator | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    """Forward process: each NUCLEOTIDE becomes <mask> with probability t (its sequence's t).

    <pad>, <bos> and <eos> are never masked. Returns z_t (B, L) and is_masked (B, L) bool.
    """
    coin = torch.rand(input_ids.shape, device=input_ids.device, generator=generator)  # (B, L) uniform
    is_masked = (coin < t[:, None]) & is_nucleotide(input_ids)                         # (B, L)
    return input_ids.masked_fill(is_masked, MASK_ID), is_masked


def masked_nelbo(logits: torch.Tensor, input_ids: torch.Tensor, is_masked: torch.Tensor,
                 t: torch.Tensor) -> torch.Tensor:
    """Per-sequence negative ELBO in nats, from the model's logits (B, L, V) -> (B,).

    Cross-entropy only at masked positions (unmasked ones are given in the
    input; padding and markers are never masked), weighted by 1/t.
    """
    targets = input_ids.masked_fill(~is_masked, -100)             # -100 = "ignore this position"
    nll = F.cross_entropy(logits.float().transpose(1, 2), targets,  # cross_entropy wants (B, V, L)
                          ignore_index=-100, reduction="none")      # (B, L): -log p(x_i | z_t), 0 where ignored
    return nll.sum(dim=1) / t                                       # (B,)


def diffusion_loss(model, input_ids: torch.Tensor, attention_mask: torch.Tensor,
                   generator: torch.Generator | None = None) -> tuple[torch.Tensor, dict]:
    """Training objective: NELBO per nucleotide (nats), over the whole batch.

    Dividing the batch total by the number of nucleotides makes the number
    comparable across batches of different lengths.
    """
    t = sample_times(input_ids.shape[0], input_ids.device, generator)        # (B,)
    z, is_masked = mask_tokens(input_ids, t, generator)                      # (B, L), (B, L)
    logits = model(z, attention_mask)                                        # (B, L, V)
    per_sequence = masked_nelbo(logits, input_ids, is_masked, t)             # (B,) nats
    n_nucleotides = is_nucleotide(input_ids).sum()
    loss = per_sequence.sum() / n_nucleotides                                # nats per nucleotide
    stats = {"bits_per_nt": loss.detach() / math.log(2),
             "masked_fraction": is_masked.sum() / n_nucleotides}
    return loss, stats


def framed_all_masked(lengths: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """The starting point of generation: <bos> <mask> x L <eos> <pad>..., plus its attention mask."""
    device = lengths.device
    B, width = len(lengths), int(lengths.max()) + 2
    pos = torch.arange(width, device=device)[None, :]                                # (1, W)
    attention_mask = pos < (lengths[:, None] + 2)                                    # (B, W): markers count as real
    z = torch.full((B, width), MASK_ID, device=device)
    z = z.masked_fill(~attention_mask, PAD_ID)
    z[:, 0] = BOS_ID
    z[torch.arange(B, device=device), lengths + 1] = EOS_ID
    return z, attention_mask


@torch.no_grad()
def sample(model, lengths: torch.Tensor, num_steps: int, generator: torch.Generator | None = None,
           temperature: float = 1.0) -> torch.Tensor:
    """Reverse process: generate len(lengths) sequences with the given numbers of nucleotides.

    Start fully masked. Going from time t to s < t, each still-masked position
    is revealed with probability (t - s) / t and receives a letter sampled from
    the model; revealed letters are frozen. At the last step (s = 0) every
    remaining mask is revealed. Returns (B, L_max + 2) ids, framed by <bos>/<eos>.
    """
    device = next(model.parameters()).device
    z, attention_mask = framed_all_masked(lengths.to(device))                        # (B, W), (B, W)
    B, W = z.shape
    times = torch.linspace(1.0, 0.0, num_steps + 1).tolist()
    for t, s in zip(times[:-1], times[1:]):
        # The network runs in bf16, the precision it was trained in (and several times
        # faster than fp32 on this GPU); the probabilities are then formed in float64.
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=z.is_cuda):
            logits = model(z, attention_mask)
        logits = logits.double() / temperature                                        # (B, W, V)
        # float64 on purpose: sampling from low-precision probabilities is known to
        # quietly sharpen the distribution and cost diversity (Zheng et al. 2024).
        probs = torch.softmax(logits, dim=-1)                                         # (B, W, V); specials exactly 0
        proposal = torch.multinomial(probs.view(-1, probs.shape[-1]), 1,
                                     generator=generator).view(B, W)                  # (B, W) a letter everywhere
        reveal = (z == MASK_ID) & (torch.rand((B, W), device=device, generator=generator) < (t - s) / t)
        z = torch.where(reveal, proposal, z)
    return z


def sample_lengths(n: int, train_lengths: torch.Tensor, generator: torch.Generator | None = None) -> torch.Tensor:
    """Unconditional generation: draw lengths from the training set's own length distribution."""
    idx = torch.randint(len(train_lengths), (n,), generator=generator)
    return train_lengths[idx]
