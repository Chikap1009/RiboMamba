"""Target-conditioned denoiser: zero-initialised adapters reproduce the base model exactly."""

import torch

from ribomamba.data.tokenizer import BOS_ID, EOS_ID, MASK_ID, encode
from ribomamba.models.conditioned import ConditionedDenoiser, conditioned_nelbo, structure_inputs
from ribomamba.models.transformer import TransformerConfig, TransformerDenoiser


def _batch():
    seqs, structs = ["GGGGAAACCCC", "GCGCAAAAGCGC"], ["((((...))))", "((((....))))"]
    W = max(map(len, seqs)) + 2
    ids = torch.zeros((2, W), dtype=torch.long)
    mask = torch.zeros((2, W), dtype=torch.bool)
    for k, s in enumerate(seqs):
        ids[k, :len(s) + 2] = torch.tensor([BOS_ID, *encode(s).tolist(), EOS_ID])
        mask[k, :len(s) + 2] = True
    return ids, mask, structs, W


def test_zero_adapters_equal_the_base_model():
    torch.manual_seed(0)
    base = TransformerDenoiser(TransformerConfig(d_model=32, n_layers=2, n_heads=2)).eval()
    cond = ConditionedDenoiser.from_unconditional(base).eval()
    ids, mask, structs, W = _batch()
    ids[:, 3] = MASK_ID
    bracket, partner = structure_inputs(structs, W, "cpu")
    assert torch.allclose(base(ids, mask), cond(ids, mask, bracket, partner), atol=1e-6)


def test_structure_inputs_use_the_framed_layout():
    bracket, partner = structure_inputs(["((.))"], 7, "cpu")
    assert bracket[0].tolist() == [3, 1, 1, 0, 2, 2, 3]
    assert partner[0].tolist() == [-1, 5, 4, -1, 2, 1, -1]


def test_pair_messages_make_a_position_depend_on_its_partner():
    torch.manual_seed(0)
    cond = ConditionedDenoiser(TransformerConfig(d_model=32, n_layers=2, n_heads=2)).eval()
    for proj in cond.pair_proj:
        torch.nn.init.normal_(proj.weight, std=0.5)                  # adapters "trained"
    ids, mask, structs, W = _batch()
    bracket, partner = structure_inputs(structs, W, "cpu")
    a = cond(ids, mask, bracket, partner)
    none = torch.full_like(partner, -1)
    assert not torch.allclose(a, cond(ids, mask, bracket, none))
    loss, stats = conditioned_nelbo(cond.train(), ids, mask, bracket, partner)
    assert torch.isfinite(loss) and loss.item() > 0
