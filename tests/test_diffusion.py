import math

import numpy as np
import torch

from ribomamba.data.tokenizer import BOS_ID, EOS_ID, MASK_ID, PAD_ID, VOCAB_SIZE, encode
from ribomamba.diffusion.masked import (
    T_MIN, diffusion_loss, framed_all_masked, mask_tokens, masked_nelbo, sample, sample_times,
)
from ribomamba.models.transformer import TransformerConfig, TransformerDenoiser

NUCLEOTIDE_IDS = [4, 5, 6, 7]


def framed(seqs: list[str]) -> tuple[torch.Tensor, torch.Tensor]:
    """<bos> x <eos> for equal-length sequences, plus an all-True attention mask."""
    body = torch.tensor(np.array([encode(s) for s in seqs]), dtype=torch.long)
    ids = torch.cat([torch.full((len(seqs), 1), BOS_ID), body, torch.full((len(seqs), 1), EOS_ID)], dim=1)
    return ids, torch.ones_like(ids, dtype=torch.bool)


def logits_from_probs(true_ids: torch.Tensor, p_true: torch.Tensor) -> torch.Tensor:
    """Logits whose softmax gives p_true to the true letter and splits the rest evenly."""
    L = len(true_ids)
    logits = torch.full((L, VOCAB_SIZE), float("-inf"))
    logits[:, NUCLEOTIDE_IDS] = torch.log((1 - p_true) / 3)[:, None]
    logits[torch.arange(L), true_ids] = torch.log(p_true)
    return logits


def test_sample_times_are_spread_evenly():
    t = sample_times(64, "cpu", torch.Generator().manual_seed(0))
    assert (t >= T_MIN).all() and (t < 1).all()
    gaps = t.sort().values.diff()
    assert torch.allclose(gaps, torch.full_like(gaps, (1 - T_MIN) / 64), atol=1e-6)


def test_masking_rate_matches_t_and_never_touches_markers_or_padding():
    g = torch.Generator().manual_seed(0)
    ids = torch.full((1000, 100), 6)
    ids[:, 0], ids[:, 79] = BOS_ID, EOS_ID            # 78 nucleotides framed by markers,
    ids[:, 80:] = PAD_ID                              # then 20 positions of padding
    z, is_masked = mask_tokens(ids, torch.full((1000,), 0.3), g)
    assert not is_masked[:, [0, 79]].any() and not is_masked[:, 80:].any()
    assert (z[:, 0] == BOS_ID).all() and (z[:, 79] == EOS_ID).all() and (z[:, 80:] == PAD_ID).all()
    rate = is_masked[:, 1:79].float().mean().item()
    assert abs(rate - 0.3) < 0.01                     # 78,000 coin flips at p = 0.3
    assert (z[is_masked] == MASK_ID).all() and (z[~is_masked] == ids[~is_masked]).all()


def test_worked_example_from_part_a():
    # GGGAAACCC, t = 1/3, positions 2, 5, 9 (1-based) masked; model gives the true
    # letters probabilities 0.6, 0.5, 0.9 there.
    ids = torch.tensor(encode("GGGAAACCC"), dtype=torch.long)
    is_masked = torch.zeros(9, dtype=torch.bool)
    is_masked[[1, 4, 8]] = True
    p_true = torch.full((9,), 0.99)
    p_true[[1, 4, 8]] = torch.tensor([0.6, 0.5, 0.9])
    logits = logits_from_probs(ids, p_true)
    nelbo = masked_nelbo(logits[None], ids[None], is_masked[None], torch.tensor([1 / 3]))
    assert math.isclose(nelbo.item(), 3 * (-math.log(0.6) - math.log(0.5) - math.log(0.9)), rel_tol=1e-6)
    assert math.isclose(nelbo.item(), 3.928, abs_tol=1e-3)
    assert math.isclose(nelbo.item() / (9 * math.log(2)), 0.630, abs_tol=1e-3)   # bits per nucleotide


class UniformModel(torch.nn.Module):
    """Knows nothing: equal odds on A, C, G, U everywhere."""
    def __init__(self):
        super().__init__()
        self.dummy = torch.nn.Parameter(torch.zeros(1))

    def forward(self, ids, attention_mask):
        logits = torch.full((*ids.shape, VOCAB_SIZE), float("-inf"))
        logits[..., NUCLEOTIDE_IDS] = 0.0
        return logits


def test_a_model_that_knows_nothing_scores_two_bits():
    # Each masked position costs ln 4; about t*L are masked; the 1/t weight cancels t.
    # So the expected NELBO is exactly L ln 4 per sequence = 2 bits per nucleotide.
    g = torch.Generator().manual_seed(0)
    body = torch.randint(4, 8, (256, 50))
    ids = torch.cat([torch.full((256, 1), BOS_ID), body, torch.full((256, 1), EOS_ID)], dim=1)
    attention = torch.ones_like(ids, dtype=torch.bool)
    values = [diffusion_loss(UniformModel(), ids, attention, g)[1]["bits_per_nt"].item() for _ in range(40)]
    assert abs(sum(values) / len(values) - 2.0) < 0.03


def test_generation_starts_framed_and_fully_masked():
    z, attention = framed_all_masked(torch.tensor([3, 1]))
    assert z.tolist() == [[BOS_ID, MASK_ID, MASK_ID, MASK_ID, EOS_ID],
                          [BOS_ID, MASK_ID, EOS_ID, PAD_ID, PAD_ID]]
    assert attention.tolist() == [[True] * 5, [True, True, True, False, False]]


def test_sampler_fills_every_position_and_respects_lengths():
    torch.manual_seed(0)
    model = TransformerDenoiser(TransformerConfig(d_model=32, n_layers=2, n_heads=4)).eval()
    lengths = torch.tensor([12, 5, 20])
    for steps in (1, 4, 20):
        out = sample(model, lengths, num_steps=steps, generator=torch.Generator().manual_seed(1))
        assert out.shape == (3, 22)
        for row, n in zip(out, lengths):
            assert row[0] == BOS_ID and row[n + 1] == EOS_ID
            assert ((row[1:n + 1] >= 4) & (row[1:n + 1] <= 7)).all()   # only A, C, G, U in between
            assert (row[n + 2:] == PAD_ID).all()


def test_tiny_model_can_memorise_four_sequences():
    # The standard "can it learn at all?" check. 4 fixed sequences, each repeated
    # 16x per batch with different masks; a tiny model; 1,000 steps. The loss
    # must fall far below the 2-bit know-nothing level.
    torch.manual_seed(0)
    ids, attention = framed(["GGGAAACCCUUAGC", "ACGUACGUAACCGG", "UUUUGGGGAAAACC", "GCGCAUAUGCGCAU"])
    ids, attention = ids.repeat(16, 1), attention.repeat(16, 1)
    model = TransformerDenoiser(TransformerConfig(d_model=64, n_layers=2, n_heads=4))
    optimiser = torch.optim.AdamW(model.parameters(), lr=1e-3)
    g = torch.Generator().manual_seed(0)
    for _ in range(1000):
        loss, _ = diffusion_loss(model, ids, attention, g)
        optimiser.zero_grad()
        loss.backward()
        optimiser.step()
    with torch.no_grad():
        final = np.mean([diffusion_loss(model, ids, attention, g)[1]["bits_per_nt"].item() for _ in range(20)])
    assert final < 0.6
