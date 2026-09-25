"""Left-to-right generation: training objective, exact likelihood and sampler (Phase 4, the AR Mamba).

The framed sequence  <bos> x_1 ... x_L <eos>  is scored with the chain rule (Phase 2):

    -log p = sum over t = 1 .. L+1 of  -log p(token_t | token_0 ... token_{t-1})

with token_0 = <bos> and token_{L+1} = <eos>. The model's output at position i is its
prediction for position i + 1 ("shift by one"), so ONE forward pass scores every token.
The value is exact, not an upper bound like the diffusion NELBO, so the protocol reports
AR-vs-diffusion likelihood as a secondary, not like-for-like number (P7).

Bits per nucleotide = that total / (L ln 2): the protocol's definition (P6, "the exact
negative log-likelihood of the framed sequence"). It includes the cost of predicting <eos>,
i.e. of the length; the letters-only value (without that term) is computed alongside.
"""

import math

import torch
import torch.nn.functional as F

from ribomamba.data.tokenizer import BOS_ID, EOS_ID, PAD_ID, is_nucleotide

IGNORE = -100    # cross_entropy's "no target here"


def next_token_targets(input_ids: torch.Tensor) -> torch.Tensor:
    """(B, W) framed, right-padded ids -> (B, W) the token that FOLLOWS each position, IGNORE where none.

    Example (L = 3):  input   <bos>  G   C   A    <eos>  <pad>
                      target    G    C   A  <eos>  ign    ign
    """
    targets = torch.full_like(input_ids, IGNORE)
    targets[:, :-1] = input_ids[:, 1:]                                     # shift left by one
    return targets.masked_fill(targets == PAD_ID, IGNORE)                  # nothing to predict after <eos>


def ar_nll_per_sequence(logits: torch.Tensor, input_ids: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Exact negative log-likelihood in nats: (framed sequence incl. <eos>, letters only), each (B,)."""
    targets = next_token_targets(input_ids)                                        # (B, W)
    nll = F.cross_entropy(logits.float().transpose(1, 2), targets,                 # cross_entropy wants (B, V, W)
                          ignore_index=IGNORE, reduction="none")                   # (B, W), 0 where ignored
    letters = nll.masked_fill(~is_nucleotide(targets), 0.0)                        # drop the <eos> term
    return nll.sum(dim=1), letters.sum(dim=1)


def ar_loss(model, input_ids: torch.Tensor, attention_mask: torch.Tensor,
            generator: torch.Generator | None = None) -> tuple[torch.Tensor, dict]:
    """Training objective: exact NLL of the framed sequences, in nats per nucleotide over the batch.

    Same signature and normalisation as diffusion_loss, so scripts/train.py treats both alike.
    `generator` is unused: nothing in this objective is random.
    """
    logits = model(input_ids, attention_mask)                                      # (B, W, V)
    framed, letters = ar_nll_per_sequence(logits, input_ids)                       # (B,), (B,)
    n_nucleotides = is_nucleotide(input_ids).sum()
    loss = framed.sum() / n_nucleotides                                            # nats per nucleotide
    stats = {"bits_per_nt": loss.detach() / math.log(2),
             "letters_bits_per_nt": letters.sum().detach() / n_nucleotides / math.log(2)}
    return loss, stats


@torch.no_grad()
def sample_ar(model, lengths: torch.Tensor, generator: torch.Generator | None = None,
              temperature: float = 1.0) -> torch.Tensor:
    """Generate len(lengths) sequences left to right, each with EXACTLY its given number of letters.

    Length constraint (protocol P5): <eos> is forbidden while a sequence is shorter than its
    target and forced when it gets there; positions after <eos> are <pad>. So the AR model
    receives the same lengths as the diffusion models. Returns (B, L_max + 2) framed ids.

    Each step reruns the model on the whole prefix and reads its last position. Carrying the
    Mamba state forward one letter at a time would be cheaper, but it runs a different kernel;
    rerunning uses exactly the computation the likelihood is measured with.
    """
    device = next(model.parameters()).device
    lengths = lengths.to(device)                                                   # (B,) letters per sequence
    B, W = len(lengths), int(lengths.max()) + 2
    ids = torch.full((B, W), PAD_ID, device=device)
    ids[:, 0] = BOS_ID
    positions = torch.arange(W, device=device)
    for i in range(1, W):                                                          # choose the token at position i
        mask = positions[None, :i] < (lengths[:, None] + 2)                        # (B, i) real framed positions
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=ids.is_cuda):
            logits = model(ids[:, :i], mask)[:, -1]                                # (B, V): prediction for position i
        logits = logits.double() / temperature                                     # float64, as the diffusion sampler
        logits[:, EOS_ID] = torch.where(i <= lengths, float("-inf"), logits[:, EOS_ID])   # too early to stop
        token = torch.multinomial(torch.softmax(logits, dim=-1), 1, generator=generator).squeeze(1)   # (B,)
        token = torch.where(i == lengths + 1, EOS_ID, token)                       # target length reached: stop
        ids[:, i] = torch.where(i > lengths + 1, PAD_ID, token)                    # already stopped: padding
    return ids
