import pytest
import torch

from ribomamba.data.tokenizer import BOS_ID, EOS_ID, MASK_ID, PAD_ID, VOCAB_SIZE
from ribomamba.models.transformer import (
    RotaryEmbedding, TransformerConfig, TransformerDenoiser, count_parameters,
)

SMALL = TransformerConfig(d_model=32, n_layers=2, n_heads=4)


@pytest.fixture
def model():
    torch.manual_seed(0)
    return TransformerDenoiser(SMALL).eval()


def test_output_shape_and_forbidden_tokens(model):
    ids = torch.tensor([[6, 6, 6, MASK_ID, 4, 4, 5, 5, 5]])            # (B=1, L=9)
    logits = model(ids, torch.ones_like(ids, dtype=torch.bool))
    assert logits.shape == (1, 9, VOCAB_SIZE)
    assert torch.isinf(logits[..., :4]).all()                          # <pad> <mask> <bos> <eos>: -inf
    assert torch.isfinite(logits[..., 4:]).all()                       # A C G U: real scores


def test_padding_cannot_change_real_outputs(model):
    # The same 5-letter sequence, alone and padded inside a batch with a longer one.
    short = torch.tensor([[6, MASK_ID, 4, 7, 5]])
    alone = model(short, torch.ones_like(short, dtype=torch.bool))                     # (1, 5, V)
    batch = torch.tensor([[6, MASK_ID, 4, 7, 5, PAD_ID, PAD_ID, PAD_ID],
                          [4, 5, 6, 7, 4, 5, 6, MASK_ID]])
    mask = torch.tensor([[True] * 5 + [False] * 3, [True] * 8])
    padded = model(batch, mask)                                                        # (2, 8, V)
    torch.testing.assert_close(padded[0, :5, 4:], alone[0, :, 4:], atol=1e-5, rtol=1e-5)
    # Changing what sits in the padding changes nothing either.
    batch[0, 5:] = torch.tensor([4, 5, 6])
    torch.testing.assert_close(model(batch, mask)[0, :5, 4:], alone[0, :, 4:], atol=1e-5, rtol=1e-5)


def test_information_flows_in_both_directions(model):
    ids = torch.tensor([[6, 6, MASK_ID, 4, 4, 4, 5, 5, 5]])
    mask = torch.ones_like(ids, dtype=torch.bool)
    before = model(ids, mask)[0, 2]
    ids[0, 8] = 6                                     # change the LAST letter...
    after = model(ids, mask)[0, 2]
    assert not torch.allclose(before[4:], after[4:])  # ...and position 2 (earlier) notices: no causal mask


def test_all_masked_input_is_position_blind_without_markers(model):
    # Why sequences are framed <bos> ... <eos> (D-010): with every position
    # holding <mask>, every value vector is identical, so any attention-weighted
    # average is that same vector, and RoPE (relative only) can't help.
    mask = torch.ones(1, 9, dtype=torch.bool)
    bare = model(torch.full((1, 9), MASK_ID), mask)[0, :, 4:]               # (9, 4)
    assert torch.allclose(bare, bare[0].expand_as(bare), atol=1e-5)        # identical at every position
    framed = torch.tensor([[BOS_ID] + [MASK_ID] * 7 + [EOS_ID]])
    out = model(framed, mask)[0, 1:8, 4:]                                  # (7, 4)
    assert not torch.allclose(out, out[0].expand_as(out), atol=1e-5)       # markers break the symmetry


def test_rope_scores_depend_only_on_offset():
    rope = RotaryEmbedding(head_dim=8, base=10000.0)
    torch.manual_seed(1)
    q, k = torch.randn(8), torch.randn(8)

    def score(m, n, length=20):
        qs = torch.zeros(1, 1, length, 8); qs[0, 0, m] = q
        ks = torch.zeros(1, 1, length, 8); ks[0, 0, n] = k
        return (rope(qs)[0, 0, m] * rope(ks)[0, 0, n]).sum()

    assert torch.isclose(score(2, 5), score(10, 13), atol=1e-5)       # same offset (3): same score
    assert not torch.isclose(score(2, 5), score(2, 9), atol=1e-3)     # different offset: different score


def test_dropout_is_active_in_training_and_off_in_evaluation():
    torch.manual_seed(0)
    model = TransformerDenoiser(TransformerConfig(d_model=32, n_layers=2, n_heads=4, dropout=0.2))
    ids = torch.tensor([[BOS_ID, 6, MASK_ID, 4, 7, 5, EOS_ID]])
    mask = torch.ones_like(ids, dtype=torch.bool)
    model.train()
    assert not torch.allclose(model(ids, mask)[..., 4:], model(ids, mask)[..., 4:])   # random each call
    model.eval()
    torch.testing.assert_close(model(ids, mask), model(ids, mask))                  # deterministic


def test_parameter_count_matches_formula():
    d, N, V = SMALL.d_model, SMALL.n_layers, VOCAB_SIZE
    # per block: 12 d^2 (attention 4 d^2 + MLP 8 d^2) + two LayerNorms (2d each);
    # plus embedding and head (V x d each) and the final LayerNorm (2d)
    expected = N * (12 * d * d + 4 * d) + 2 * V * d + 2 * d
    assert count_parameters(TransformerDenoiser(SMALL)) == expected
