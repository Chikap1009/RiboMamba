import numpy as np
import polars as pl
import pytest
import torch

from ribomamba.data.dataset import BucketBatchSampler, RNADataset, collate
from ribomamba.data.tokenizer import BOS_ID, EOS_ID, PAD_ID, decode

SEQS = ["GGGAAACCC", "ACGU", "UUUUAAAAGGGGCCCC", "GCAUAGC", "AAAAAAAAAAAAAAAAAAAAAAAAA"]


@pytest.fixture
def tiny_split(tmp_path):
    pl.DataFrame({"sequence": SEQS}).write_parquet(tmp_path / "tiny.parquet")
    return tmp_path


def test_dataset_returns_each_sequence(tiny_split):
    ds = RNADataset("tiny", data_dir=tiny_split)
    assert len(ds) == len(SEQS)
    assert [decode(ds[i]) for i in range(len(ds))] == SEQS
    assert ds[0].dtype == torch.long


def test_bos_eos_are_added(tiny_split):
    ds = RNADataset("tiny", add_bos=True, add_eos=True, data_dir=tiny_split)
    item = ds[1]                                   # "ACGU"
    assert item.tolist() == [BOS_ID, 4, 5, 6, 7, EOS_ID]
    assert ds.token_lengths()[1] == 6


def test_collate_pads_and_masks():
    batch = [torch.tensor([6, 6, 6, 4, 4, 4, 5, 5, 5]), torch.tensor([4, 5, 6, 7])]
    out = collate(batch)
    assert out["input_ids"].shape == (2, 9)
    assert out["input_ids"][1].tolist() == [4, 5, 6, 7] + [PAD_ID] * 5
    assert out["attention_mask"].dtype == torch.bool
    assert out["attention_mask"].sum(dim=1).tolist() == [9, 4]   # real positions per row


def test_bucket_sampler_uses_every_index_exactly_once():
    lengths = np.random.default_rng(0).integers(20, 256, size=1000)
    sampler = BucketBatchSampler(lengths, batch_size=32, pool_batches=10, seed=1)
    seen = np.concatenate([np.array(b) for b in sampler])
    assert sorted(seen.tolist()) == list(range(1000))


def test_bucket_sampler_reduces_padding():
    lengths = np.random.default_rng(0).integers(20, 256, size=5000)

    def padding_fraction(batches):
        real = sum(lengths[b].sum() for b in batches)
        total = sum(len(b) * lengths[b].max() for b in batches)
        return 1 - real / total

    bucketed = [np.array(b) for b in BucketBatchSampler(lengths, batch_size=32, seed=1)]
    random = np.array_split(np.random.default_rng(1).permutation(5000), 5000 // 32)
    assert padding_fraction(bucketed) < 0.05 < padding_fraction(random)


def test_token_budget_batches_respect_the_budget_and_cover_everything():
    lengths = np.random.default_rng(0).integers(20, 258, size=5000)
    sampler = BucketBatchSampler(lengths, max_tokens=4096, seed=2)
    batches = [np.array(b) for b in sampler]
    assert all(len(b) * lengths[b].max() <= 4096 for b in batches)       # padded slots within budget
    assert sorted(np.concatenate(batches).tolist()) == list(range(5000))  # every sequence exactly once
    sizes = [len(b) for b in batches]
    assert max(sizes) > 3 * min(sizes)                                     # short sequences -> bigger batches


def test_bucket_sampler_is_reproducible_and_changes_per_epoch():
    lengths = np.arange(500)
    a, b = BucketBatchSampler(lengths, 16, seed=3), BucketBatchSampler(lengths, 16, seed=3)
    assert list(a) == list(b)                     # same seed, same epoch -> same batches
    first = list(a)
    a.set_epoch(1)
    assert list(a) != first                       # new epoch -> new order
