"""The repair pilot's validation manifest: deterministic, stratified, split, tamper-evident, test-free."""

import json
from collections import Counter

import pytest

from ribomamba.design import manifest as mf

needs_source = pytest.mark.skipif(not mf.SOURCE.exists(), reason="data/targets/rfam_val.parquet not built")


@pytest.fixture(scope="module")
def built():
    return mf.build_manifest()


@needs_source
def test_source_is_the_recorded_validation_file():
    assert mf.sha256_file(mf.SOURCE) == mf.SOURCE_SHA256


@needs_source
def test_rebuild_reproduces_the_committed_manifest(built):
    committed = mf.load_manifest()
    assert built["content_sha256"] == committed["content_sha256"]
    assert built == committed


@needs_source
def test_selection_is_stratified_split_and_eligible(built):
    targets = built["targets"]
    assert len(targets) == 64 and len({t["id"] for t in targets}) == 64
    assert len({t["structure"] for t in targets}) == 64
    cells = Counter((t["length_bin"], t["paired_bin"]) for t in targets)
    assert sorted(cells) == [(lb, pb) for lb in range(4) for pb in range(4)] and set(cells.values()) == {4}
    for cell in cells:
        subsets = Counter(t["subset"] for t in targets if (t["length_bin"], t["paired_bin"]) == cell)
        assert subsets == {"development": 2, "confirmation": 2}
    smoke = [t for t in targets if t["smoke"]]
    assert len(smoke) == 8 and all(t["subset"] == "development" for t in smoke)
    assert sorted((t["length_bin"], t["paired_bin"] // 2) for t in smoke) == [(lb, h) for lb in range(4)
                                                                                 for h in (0, 1)]
    for t in targets:
        assert len(t["structure"]) <= 256 and set(t["structure"]) <= set("().")
        assert t["pairs"] >= 4 and len(t["native_sequence"]) == len(t["structure"])
        assert t["native_control"]["mfe_backtrack"]            # positive control: the native solves it
    assert built["funnel"]["eligible"] == 402 - len(built["exclusions"])


@needs_source
def test_subsets(built):
    assert [t["id"] for t in mf.select(built, "smoke")] == [t["id"] for t in built["targets"] if t["smoke"]]
    dev, conf = mf.select(built, "development"), mf.select(built, "confirmation")
    assert len(dev) == len(conf) == 32 and not {t["id"] for t in dev} & {t["id"] for t in conf}
    assert len(mf.select(built, "all")) == 64
    with pytest.raises(ValueError):
        mf.select(built, "test")


@needs_source
def test_an_edited_manifest_is_refused(tmp_path, built):
    edited = json.loads(json.dumps(built))
    edited["targets"][0]["structure"] = edited["targets"][0]["structure"].replace("(", ".", 1)
    path = tmp_path / "m.json"
    path.write_text(json.dumps(edited))
    with pytest.raises(ValueError, match="content hash"):
        mf.load_manifest(path)
    with pytest.raises(FileExistsError):                     # a different manifest never overwrites
        mf.write_manifest(built, path)


def test_test_targets_are_refused(tmp_path):
    with pytest.raises(PermissionError):
        mf.build_manifest(tmp_path / "rfam_test.parquet")


@pytest.mark.parametrize("target, native, reason", [
    ("((((....))))[", "GGGGAAAACCCCA", "pseudoknot"),
    ("((((....)))", "GGGGAAAACCC", "unbalanced"),
    ("((.))", "GGACC", "fewer than 4"),
    ("((((.))))....", "GGGGACCCCAAAA", "encloses fewer"),
    ("((((....))))", "GGGGAAAACCCA", "cannot form"),
    ("((((....))))", "GGGGAAAACCCN", "outside A/C/G/U"),
    ("((((....))))", "GGGGAAAACCC", "length differs"),
])
def test_eligibility_rules_name_their_reason(target, native, reason):
    assert reason in mf._ineligible({"target": target, "sequence": native, "native_mfe_match": True})


def test_equal_bins_are_deterministic_and_balanced():
    bins = mf._equal_bins([5, 1, 5, 3, 5, 2, 4, 5], list("abcdefgh"), 4)
    assert Counter(bins) == {0: 2, 1: 2, 2: 2, 3: 2}
    assert bins == mf._equal_bins([5, 1, 5, 3, 5, 2, 4, 5], list("abcdefgh"), 4)
