import numpy as np
import pytest

from ribomamba.data.tokenizer import (
    BOS_ID, EOS_ID, MASK_ID, PAD_ID, VOCAB, VOCAB_SIZE, decode, encode,
)


def test_vocabulary_is_frozen():
    # Checkpoints depend on these exact numbers. If this test fails, a change
    # would scramble every trained model: do not "fix" the test, revert the change.
    assert VOCAB == ["<pad>", "<mask>", "<bos>", "<eos>", "A", "C", "G", "U"]
    assert (PAD_ID, MASK_ID, BOS_ID, EOS_ID, VOCAB_SIZE) == (0, 1, 2, 3, 8)


def test_encode_known_sequence():
    assert encode("GGGAAACCC").tolist() == [6, 6, 6, 4, 4, 4, 5, 5, 5]


def test_round_trip():
    seq = "ACGUUGCAACGU"
    assert decode(encode(seq)) == seq


def test_decode_handles_specials():
    ids = [BOS_ID, 6, MASK_ID, 5, EOS_ID, PAD_ID]
    assert decode(ids) == "GC"
    assert decode(ids, skip_special=False) == "<bos>G<mask>C<eos><pad>"


@pytest.mark.parametrize("bad", ["ACGT", "ACGN", "acgu", "AC-GU"])
def test_rejects_non_acgu(bad):
    with pytest.raises(ValueError):
        encode(bad)


def test_encode_returns_small_integers():
    ids = encode("ACGU")
    assert ids.dtype == np.int8   # 1 byte per nucleotide in memory
