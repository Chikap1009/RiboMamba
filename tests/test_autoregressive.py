import math

import torch
import torch.nn as nn

from ribomamba.autoregressive import IGNORE, ar_loss, ar_nll_per_sequence, next_token_targets, sample_ar
from ribomamba.data.tokenizer import BOS_ID, EOS_ID, MASK_ID, PAD_ID, VOCAB_SIZE, decode, is_nucleotide


class FixedScores(nn.Module):
    """Stand-in model: the same scores at every position; <pad>, <mask>, <bos> forbidden (as the AR Mamba)."""

    def __init__(self, scores: dict[int, float]):
        super().__init__()
        logits = torch.full((VOCAB_SIZE,), float("-inf"))
        for token, score in scores.items():
            logits[token] = score
        self.register_buffer("logits", logits)
        self.dummy = nn.Parameter(torch.zeros(1))                 # so next(model.parameters()) finds a device

    def forward(self, input_ids, attention_mask):
        return self.logits.expand(*input_ids.shape, VOCAB_SIZE)   # (B, L, V)


LETTERS_AND_EOS = [4, 5, 6, 7, EOS_ID]


def framed(*sequences: str) -> torch.Tensor:
    ids = {"A": 4, "C": 5, "G": 6, "U": 7}
    width = max(len(s) for s in sequences) + 2
    rows = [[BOS_ID] + [ids[c] for c in s] + [EOS_ID] + [PAD_ID] * (width - len(s) - 2) for s in sequences]
    return torch.tensor(rows)


def test_targets_are_the_next_token_and_nothing_after_eos():
    targets = next_token_targets(framed("GCA", "G"))
    assert targets.tolist() == [[6, 5, 4, EOS_ID, IGNORE], [6, EOS_ID, IGNORE, IGNORE, IGNORE]]


def test_hand_worked_chain_rule():
    # Scores 0 everywhere except G at ln 2: p(G) = 2/6 = 1/3; A, C, U, <eos> 1/6 each.
    # <bos> G G A <eos>:  -ln(1/3) - ln(1/3) - ln(1/6) [A] - ln(1/6) [<eos>] = 2 ln 3 + 2 ln 6 = 5.781 nats.
    model = FixedScores({4: 0.0, 5: 0.0, 6: math.log(2), 7: 0.0, EOS_ID: 0.0})
    ids = framed("GGA")
    total, letters = ar_nll_per_sequence(model(ids, ids != PAD_ID), ids)
    assert math.isclose(total.item(), 2 * math.log(3) + 2 * math.log(6), rel_tol=1e-6)
    assert math.isclose(letters.item(), 2 * math.log(3) + math.log(6), rel_tol=1e-6)     # without the <eos> term


def test_a_model_that_knows_nothing_costs_log5_per_token():
    # Uniform over A, C, G, U, <eos>: every predicted token costs ln 5, and a sequence of L letters
    # predicts L + 1 tokens. Padding must add nothing: lengths 3 and 1 -> (4 + 2) ln 5 over 4 letters.
    model = FixedScores({t: 0.0 for t in LETTERS_AND_EOS})
    ids = framed("GCA", "U")
    loss, stats = ar_loss(model, ids, ids != PAD_ID)
    assert math.isclose(loss.item(), 6 * math.log(5) / 4, rel_tol=1e-6)
    assert math.isclose(stats["letters_bits_per_nt"].item(), math.log2(5), rel_tol=1e-6)


def test_sampler_gives_exactly_the_requested_lengths():
    # This model would stop at once if allowed (<eos> is 99.99 % likely), so the lengths
    # can only come out right if the constraint forbids <eos> early and forces it at the end.
    model = FixedScores({4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, EOS_ID: 10.0})
    lengths = torch.tensor([5, 1, 3])
    out = sample_ar(model, lengths, generator=torch.Generator().manual_seed(0))       # (3, 7)
    assert out.shape == (3, 7)
    for row, n in zip(out, lengths.tolist()):
        assert row[0] == BOS_ID and row[n + 1] == EOS_ID
        assert is_nucleotide(row[1:n + 1]).all()
        assert (row[n + 2:] == PAD_ID).all()
        assert len(decode(row)) == n
    assert MASK_ID not in out


def test_sampler_is_reproducible_with_a_seed():
    model = FixedScores({t: 0.0 for t in LETTERS_AND_EOS})
    lengths = torch.tensor([8, 8])
    first = sample_ar(model, lengths, generator=torch.Generator().manual_seed(3))
    again = sample_ar(model, lengths, generator=torch.Generator().manual_seed(3))
    assert torch.equal(first, again)
