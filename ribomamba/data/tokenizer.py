"""Character-level RNA tokeniser: one nucleotide = one token (D-006).

The vocabulary is fixed forever. Trained checkpoints store one embedding row
per token id, so renumbering the ids would silently scramble every saved model.
tests/test_tokenizer.py pins these numbers.

    id:     0      1       2      3      4  5  6  7
    token:  <pad>  <mask>  <bos>  <eos>  A  C  G  U
"""

import numpy as np

SPECIAL_TOKENS = ["<pad>", "<mask>", "<bos>", "<eos>"]
NUCLEOTIDES = ["A", "C", "G", "U"]
VOCAB = SPECIAL_TOKENS + NUCLEOTIDES      # a token's id is its index in this list
VOCAB_SIZE = len(VOCAB)                   # 8

PAD_ID = VOCAB.index("<pad>")    # 0: filler that makes sequences in a batch equal length
MASK_ID = VOCAB.index("<mask>")  # 1: "hidden letter", the absorbing state of masked diffusion (Phase 2)
BOS_ID = VOCAB.index("<bos>")    # 2: "start writing here" for the autoregressive baseline (Phase 4)
EOS_ID = VOCAB.index("<eos>")    # 3: "I'm done", so a model can choose the sequence length

# Lookup table from ASCII byte value (0..255) to token id; -1 = not a nucleotide.
# Encoding a whole sequence is then one array-indexing step instead of a
# Python loop over characters: the software version of a ROM lookup table.
_BYTE_TO_ID = np.full(256, -1, dtype=np.int8)
for _nt in NUCLEOTIDES:
    _BYTE_TO_ID[ord(_nt)] = VOCAB.index(_nt)


def encode(sequence: str) -> np.ndarray:
    """'GGAC' -> array([6, 6, 4, 5], dtype=int8). Only A, C, G, U are accepted.

    Cleaning (scripts/prepare_data.py) guarantees this for our data; the check
    here turns any violation into a loud error instead of a silent wrong id.
    """
    raw = np.frombuffer(sequence.encode("ascii"), dtype=np.uint8)  # (L,) byte values
    ids = _BYTE_TO_ID[raw]                                          # (L,) token ids
    if (ids < 0).any():
        bad = sorted({sequence[i] for i in np.flatnonzero(ids < 0)})
        raise ValueError(f"non-ACGU characters {bad} in sequence: {sequence[:60]}")
    return ids


def decode(ids, skip_special: bool = True) -> str:
    """Token ids -> string. Specials are dropped, or kept as '<mask>' etc."""
    tokens = (VOCAB[int(i)] for i in ids)
    if skip_special:
        tokens = (t for t in tokens if t not in SPECIAL_TOKENS)
    return "".join(tokens)
