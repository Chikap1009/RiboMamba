import copy

import pytest
import torch
import torch.nn.functional as F

from ribomamba.data.tokenizer import BOS_ID, EOS_ID, MASK_ID, PAD_ID, VOCAB_SIZE
from ribomamba.diffusion.masked import diffusion_loss
from ribomamba.models.bimamba import MambaConfig, MambaModel, expected_parameters, reorder, reversal_index
from ribomamba.models.transformer import count_parameters

pytestmark = pytest.mark.skipif(not torch.cuda.is_available(), reason="the Mamba kernels need a CUDA GPU")

TINY = dict(d_model=32, n_layers=2, d_state=16, headdim=16, expand=2)    # 4 heads of 16 channels, 16-number states


def make(bidirectional: bool, dropout: float = 0.0, seed: int = 0) -> MambaModel:
    torch.manual_seed(seed)
    return MambaModel(MambaConfig(**TINY, bidirectional=bidirectional, dropout=dropout)).cuda().eval()


def ids_and_mask(rows: list[list[int]]) -> tuple[torch.Tensor, torch.Tensor]:
    """Right-pad token rows into (B, L) ids plus the mask of real positions, on the GPU."""
    width = max(len(r) for r in rows)
    ids = torch.tensor([r + [PAD_ID] * (width - len(r)) for r in rows], device="cuda")
    mask = torch.tensor([[True] * len(r) + [False] * (width - len(r)) for r in rows], device="cuda")
    return ids, mask


def test_reversal_index_reverses_each_sequence_within_its_own_length():
    mask = torch.tensor([[True, True, True, False, False], [True] * 5])
    index = reversal_index(mask)
    assert index.tolist() == [[2, 1, 0, 3, 4], [4, 3, 2, 1, 0]]          # padding stays at the right end
    x = torch.arange(10.0).view(2, 5, 1)                                  # (B=2, L=5, C=1)
    assert reorder(x, index)[0, :, 0].tolist() == [2.0, 1.0, 0.0, 3.0, 4.0]
    assert torch.equal(reorder(reorder(x, index), index), x)             # reversing twice restores the order


@pytest.mark.parametrize("bidirectional", [True, False])
def test_output_shape_and_forbidden_tokens(bidirectional):
    ids, mask = ids_and_mask([[BOS_ID, 6, 6, MASK_ID, 4, 5, 5, EOS_ID]])
    logits = make(bidirectional)(ids, mask)                               # (1, 8, V)
    assert logits.shape == (1, 8, VOCAB_SIZE)
    assert torch.isinf(logits[..., [PAD_ID, MASK_ID, BOS_ID]]).all()
    assert torch.isfinite(logits[..., 4:]).all()                           # A C G U: real scores
    # The denoiser only ever predicts letters; the AR model must be able to end a sequence.
    assert torch.isinf(logits[..., EOS_ID]).all() == bidirectional


@pytest.mark.parametrize("bidirectional", [True, False])
def test_padding_cannot_change_real_outputs(bidirectional):
    model = make(bidirectional)
    short = [BOS_ID, 6, MASK_ID, 4, 7, 5, EOS_ID]
    alone = model(*ids_and_mask([short]))                                             # (1, 7, V)
    ids, mask = ids_and_mask([short, [BOS_ID, 4, 5, 6, 7, 4, 5, 6, MASK_ID, 7, EOS_ID]])
    padded = model(ids, mask)                                                         # (2, 11, V)
    torch.testing.assert_close(padded[0, :7, 4:], alone[0, :, 4:], atol=1e-4, rtol=1e-4)
    ids[0, 7:] = torch.tensor([4, 5, 6, 7], device="cuda")                              # garbage in the padding
    torch.testing.assert_close(model(ids, mask)[0, :7, 4:], alone[0, :, 4:], atol=1e-4, rtol=1e-4)


def test_bimamba_sees_both_directions():
    model = make(bidirectional=True)
    ids, mask = ids_and_mask([[BOS_ID, 6, 6, MASK_ID, 4, 4, 4, 5, 5, 5, EOS_ID]])
    before = model(ids, mask)[0]
    changed = ids.clone()
    changed[0, 9] = 6                                                     # change the LAST letter
    after = model(changed, mask)[0]
    assert not torch.allclose(before[3, 4:], after[3, 4:])               # an earlier position notices


def test_ar_mamba_sees_only_the_past():
    model = make(bidirectional=False)
    ids, mask = ids_and_mask([[BOS_ID, 6, 6, 6, 4, 4, 4, 5, 5, 5, EOS_ID]])
    before = model(ids, mask)[0]
    changed = ids.clone()
    changed[0, 6] = 7                                                     # change position 6
    after = model(changed, mask)[0]
    torch.testing.assert_close(after[:6], before[:6], atol=1e-6, rtol=0)   # positions 0-5 cannot know
    assert not torch.allclose(before[6:, 4:], after[6:, 4:])            # from position 6 on, they do


def reference_direction(zxbcdt: torch.Tensor, m) -> torch.Tensor:
    """Textbook Mamba-2 for one direction, one letter at a time (instalment 2), float32.

    (1, L, d_in_proj) -> (1, L, d_inner): causal width-K convolution + SiLU, then per head
    h_t = exp(dt_t * A) h_{t-1} + dt_t * x_t B_t^T,  y_t = h_t C_t + D x_t,  then y * SiLU(z) and RMSNorm.
    """
    inner, N, H, P = m.d_inner, m.d_state, m.nheads, m.headdim
    z, xBC, dt = zxbcdt.split([inner, inner + 2 * N, H], dim=-1)
    K = m.d_conv
    conv = F.conv1d(F.pad(xBC.transpose(1, 2), (K - 1, 0)), m.conv1d.weight, m.conv1d.bias,
                    groups=inner + 2 * N)                                  # (1, C, L): sees t-K+1 .. t only
    x, B, C = F.silu(conv.transpose(1, 2)).split([inner, N, N], dim=-1)
    dt = F.softplus(dt + m.dt_bias)                                        # (1, L, H) step sizes, > 0
    A = -torch.exp(m.A_log)                                                # (H,) negative: stable
    x = x.view(1, -1, H, P)
    h = torch.zeros(1, H, P, N, device=zxbcdt.device)
    ys = []
    for t in range(zxbcdt.shape[1]):
        keep = torch.exp(dt[:, t] * A)                                     # (1, H) keep factor, one per head
        h = keep[..., None, None] * h + dt[:, t, :, None, None] * x[:, t, :, :, None] * B[:, t, None, None, :]
        ys.append(((h * C[:, t, None, None, :]).sum(-1) + m.D[None, :, None] * x[:, t]).reshape(1, inner))
    y = torch.stack(ys, dim=1) * F.silu(z)                                  # gate first (norm_before_gate=False)
    return y * torch.rsqrt(y.square().mean(-1, keepdim=True) + m.norm.eps) * m.norm.weight


@pytest.mark.parametrize("bidirectional", [True, False])
def test_fused_kernels_equal_the_textbook_recurrence(bidirectional):
    # The padded batch goes through the GPU kernels; each sequence ALONE goes through the loop above,
    # reversed with a plain flip. Agreement checks the kernel settings, the per-sequence reversal and
    # that padding stays out, by an independent route.
    mixer = make(bidirectional).blocks[0].mixer
    torch.manual_seed(1)
    lengths = [9, 5, 12]
    u = torch.randn(3, max(lengths), TINY["d_model"], device="cuda")
    mask = torch.arange(max(lengths), device="cuda")[None, :] < torch.tensor(lengths, device="cuda")[:, None]
    with torch.no_grad():
        fused = mixer(u, reversal_index(mask) if bidirectional else None)                   # (3, 12, d)
        for b, n in enumerate(lengths):
            row = u[b:b + 1, :n]                                                             # (1, n, d)
            if bidirectional:
                zx = mixer.fwd.in_proj(row)
                y = reference_direction(zx, mixer.fwd) + reference_direction(zx.flip(1), mixer.bwd).flip(1)
                expected = mixer.fwd.out_proj(y)
            else:
                expected = mixer.mamba.out_proj(reference_direction(mixer.mamba.in_proj(row), mixer.mamba))
            torch.testing.assert_close(fused[b:b + 1, :n], expected, atol=1e-4, rtol=1e-3)


def test_mamba_is_not_position_blind_even_without_markers():
    # Contrast with the Transformer (D-010): with every position holding <mask>, attention gives every
    # position the same output. A scan does not: position t has read t letters, so its state differs.
    model = make(bidirectional=True)
    ids, mask = ids_and_mask([[MASK_ID] * 9])
    out = model(ids, mask)[0, :, 4:]                                      # (9, 4)
    assert not torch.allclose(out, out[0].expand_as(out), atol=1e-4)


def test_diffusion_training_reaches_both_directions_and_the_ema_copy_matches():
    model = make(bidirectional=True).train()
    ids, mask = ids_and_mask([[BOS_ID, 6, 6, 4, 4, 5, 5, EOS_ID], [BOS_ID, 4, 7, 6, EOS_ID]])
    g = torch.Generator(device="cuda").manual_seed(0)
    loss, _ = diffusion_loss(model, ids, mask, g)
    loss.backward()
    mixer = model.blocks[0].mixer
    for p in (mixer.fwd.A_log, mixer.bwd.A_log, mixer.fwd.conv1d.weight, mixer.bwd.conv1d.weight):
        assert p.grad is not None and p.grad.abs().sum() > 0            # both directions are trained
    model.eval()
    twin = copy.deepcopy(model)                                            # how train.py makes the EMA model
    torch.testing.assert_close(twin(ids, mask), model(ids, mask))


def test_dropout_is_active_in_training_and_off_in_evaluation():
    model = make(bidirectional=True, dropout=0.2)
    ids, mask = ids_and_mask([[BOS_ID, 6, MASK_ID, 4, 7, 5, EOS_ID]])
    model.train()
    assert not torch.allclose(model(ids, mask)[..., 4:], model(ids, mask)[..., 4:])
    model.eval()
    torch.testing.assert_close(model(ids, mask), model(ids, mask))


def test_rows_padded_on_the_left_are_refused():
    ids = torch.tensor([[PAD_ID, BOS_ID, 6, EOS_ID]], device="cuda")
    mask = torch.tensor([[False, True, True, True]], device="cuda")
    with pytest.raises(ValueError, match="right end"):
        make(bidirectional=True)(ids, mask)


@pytest.mark.parametrize("bidirectional", [True, False])
def test_parameter_count_matches_formula(bidirectional):
    cfg = MambaConfig(**TINY, bidirectional=bidirectional)
    assert count_parameters(MambaModel(cfg)) == expected_parameters(cfg)


def test_phase4_sizes_sit_inside_the_protocols_two_percent():
    # D-015 (depth matching): width 384 as the Transformer, 14 layers each; target 14,174,976 +- 2 %.
    assert expected_parameters(MambaConfig(bidirectional=True)) == 14_010_608      # -1.16 %
    assert expected_parameters(MambaConfig(bidirectional=False)) == 13_927_672     # -1.74 %
    assert count_parameters(MambaModel(MambaConfig(bidirectional=True))) == 14_010_608
