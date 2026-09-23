"""PyTorch Dataset, padding, and length-bucketed batching for RNA sequences.

How a batch is born:

    parquet file ──▶ RNADataset[i] ──▶ 1-D tensor of token ids, e.g. (L_i,)
                                            │  many of these, different L_i
                                            ▼
    BucketBatchSampler ──▶ which indices go together (similar lengths)
                                            │
                                            ▼
    collate() ──▶ {"input_ids": (B, L_max), "attention_mask": (B, L_max)}
"""

import numpy as np
import polars as pl
import torch
from torch.utils.data import DataLoader, Dataset, Sampler

from ribomamba.data.tokenizer import BOS_ID, EOS_ID, PAD_ID, encode
from ribomamba.paths import PROCESSED_DIR


class RNADataset(Dataset):
    """One split (train / val / test) of cleaned sequences, stored as token ids.

    All sequences are concatenated into ONE flat int8 array, with an `offsets`
    array saying where each starts. Sequence i is flat[offsets[i]:offsets[i+1]].
    Like a memory plus a table of base addresses: one allocation instead of
    hundreds of thousands of small Python objects. That keeps memory at about
    1 byte per nucleotide and stays cheap when DataLoader worker processes
    share it.
    """

    def __init__(self, split: str, add_bos: bool = False, add_eos: bool = False,
                 data_dir=PROCESSED_DIR):
        sequences = pl.read_parquet(data_dir / f"{split}.parquet", columns=["sequence"])["sequence"]
        self.lengths = sequences.str.len_bytes().to_numpy().astype(np.int64)     # (N,)
        self.offsets = np.concatenate([[0], np.cumsum(self.lengths)])            # (N+1,)
        self.flat = encode("".join(sequences.to_list()))                         # (total nucleotides,) int8
        self.add_bos, self.add_eos = add_bos, add_eos

    def __len__(self) -> int:
        return len(self.lengths)

    def __getitem__(self, i: int) -> torch.Tensor:
        ids = torch.from_numpy(self.flat[self.offsets[i]:self.offsets[i + 1]]).long()  # (L_i,)
        if self.add_bos:
            ids = torch.cat([torch.tensor([BOS_ID]), ids])                             # (L_i + 1,)
        if self.add_eos:
            ids = torch.cat([ids, torch.tensor([EOS_ID])])
        return ids

    def token_lengths(self) -> np.ndarray:
        """Length of each item as returned by __getitem__, specials included."""
        return self.lengths + int(self.add_bos) + int(self.add_eos)


def collate(batch: list[torch.Tensor]) -> dict[str, torch.Tensor]:
    """Pad a list of 1-D id tensors into one rectangle, plus the mask of real positions.

    Example, B = 2:
        [6,6,6,4,4,4,5,5,5]  and  [4,5,6,7]
    ->  input_ids      = [[6,6,6,4,4,4,5,5,5],
                          [4,5,6,7,0,0,0,0,0]]        (B=2, L_max=9)
        attention_mask = [[T,T,T,T,T,T,T,T,T],
                          [T,T,T,T,F,F,F,F,F]]        (B=2, L_max=9)  True = real
    """
    lengths = torch.tensor([len(x) for x in batch])                                    # (B,)
    input_ids = torch.nn.utils.rnn.pad_sequence(batch, batch_first=True,
                                                padding_value=PAD_ID)                   # (B, L_max)
    positions = torch.arange(input_ids.shape[1])                                       # (L_max,)
    # Broadcasting: (1, L_max) < (B, 1) compares every position with every row's
    # length, producing (B, L_max). Position p is real iff p < that row's length.
    attention_mask = positions[None, :] < lengths[:, None]                             # (B, L_max) bool
    return {"input_ids": input_ids, "attention_mask": attention_mask}


class BucketBatchSampler(Sampler[list[int]]):
    """Yields batches of indices whose sequences have similar lengths.

    Each epoch:
      1. shuffle all indices (randomness between epochs);
      2. cut them into "pools" of batch_size * pool_batches;
      3. sort each pool by length, then cut it into batches (similar lengths
         end up together, so little padding);
      4. shuffle the order of the batches (so training doesn't see short
         sequences first and long ones last).
    Sorting inside a pool rather than over the whole dataset keeps batches
    random enough to train on while still cutting most of the padding.

    Batch size is given in one of two ways:
      batch_size=n   every batch has n sequences (Phase 1 default);
      max_tokens=m   every batch holds as many sequences as fit in m padded
                     slots (count x longest length <= m), so every training
                     step costs about the same memory and time whether the
                     sequences are short or long (D-011).
    """

    def __init__(self, lengths: np.ndarray, batch_size: int | None = None, max_tokens: int | None = None,
                 pool_batches: int = 100, shuffle: bool = True, drop_last: bool = False, seed: int = 0):
        assert (batch_size is None) != (max_tokens is None), "give exactly one of batch_size, max_tokens"
        self.lengths = np.asarray(lengths)
        self.batch_size, self.max_tokens, self.pool_batches = batch_size, max_tokens, pool_batches
        self.shuffle, self.drop_last, self.seed = shuffle, drop_last, seed
        self.epoch = 0
        # pool size in sequences: 100 batches' worth (for max_tokens, estimated at the median length)
        per_batch = batch_size or max(1, max_tokens // int(np.median(self.lengths)))
        self.pool_size = per_batch * pool_batches

    def set_epoch(self, epoch: int) -> None:
        """Call once per epoch so each epoch shuffles differently but reproducibly."""
        self.epoch = epoch

    def _cut(self, pool: np.ndarray) -> list[np.ndarray]:
        """Cut a length-sorted pool into batches."""
        if self.batch_size is not None:
            return [pool[i:i + self.batch_size] for i in range(0, len(pool), self.batch_size)]
        batches, start = [], 0
        for end in range(1, len(pool) + 1):
            # the pool is sorted, so the newest sequence is the longest: cost = count x its length
            if (end - start) * self.lengths[pool[end - 1]] > self.max_tokens and end - 1 > start:
                batches.append(pool[start:end - 1])
                start = end - 1
        batches.append(pool[start:])
        return batches

    def _batches(self) -> list[np.ndarray]:
        rng = np.random.default_rng((self.seed, self.epoch))
        order = rng.permutation(len(self.lengths)) if self.shuffle else np.arange(len(self.lengths))
        batches = []
        for start in range(0, len(order), self.pool_size):
            pool = order[start:start + self.pool_size]
            pool = pool[np.argsort(self.lengths[pool], kind="stable")]
            batches += self._cut(pool)
        if self.drop_last and self.batch_size is not None:
            batches = [b for b in batches if len(b) == self.batch_size]
        if self.shuffle:
            batches = [batches[i] for i in rng.permutation(len(batches))]
        return batches

    def __iter__(self):
        for batch in self._batches():
            yield batch.tolist()

    def __len__(self) -> int:
        return len(self._batches())


def make_dataloader(split: str, batch_size: int | None = None, max_tokens: int | None = None,
                    shuffle: bool = True, bucketing: bool = True, add_bos: bool = False,
                    add_eos: bool = False, num_workers: int = 2, seed: int = 0,
                    data_dir=PROCESSED_DIR) -> DataLoader:
    """The one call training code makes to get batches of a split."""
    dataset = RNADataset(split, add_bos=add_bos, add_eos=add_eos, data_dir=data_dir)
    common = dict(collate_fn=collate, num_workers=num_workers, pin_memory=torch.cuda.is_available())
    if bucketing or max_tokens is not None:
        sampler = BucketBatchSampler(dataset.token_lengths(), batch_size=batch_size, max_tokens=max_tokens,
                                     shuffle=shuffle, seed=seed)
        return DataLoader(dataset, batch_sampler=sampler, **common)
    generator = torch.Generator().manual_seed(seed)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, generator=generator, **common)
