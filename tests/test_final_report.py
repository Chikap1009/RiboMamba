"""Final report: an errored unit counts as unsolved with no design, whatever its partial trace holds."""

import json
import math
import sys

import polars as pl

from ribomamba.design import runner
from ribomamba.paths import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import final_report  # noqa: E402

MANIFEST = {"name": "toy", "content_sha256": "0" * 64}
TARGETS = [{"id": "toy:a", "structure": "((((....))))"}, {"id": "toy:b", "structure": "((((....))))..(((...)))"}]


def test_error_units_are_unsolved_with_no_design_in_every_figure(tmp_path):
    cfg = runner.make_config(MANIFEST, "toy", TARGETS, ["random_pairs"], [0, 1], 12)
    runner.run(tmp_path, cfg, TARGETS, workers=1, progress=lambda *a: None)
    before = final_report.per_unit(tmp_path)
    key = runner.unit_key("random_pairs", "toy:a", 0)
    solved = before.filter((pl.col("target_id") == "toy:a") & (pl.col("seed") == 0))
    assert solved["success_umfe"].all() and solved["sequence"].is_not_null().all()   # the trace HAS a success

    status_path = runner.unit_paths(tmp_path, key)[1]
    status = json.loads(status_path.read_text())
    status_path.write_text(json.dumps({**status, "status": "error", "reason": "Traceback ...\nRuntimeError: x"}))
    after = final_report.per_unit(tmp_path)
    assert after.height == before.height
    bad = after.filter((pl.col("target_id") == "toy:a") & (pl.col("seed") == 0))
    assert bad.height == len(final_report.WALLS) and bad["errored"].all()
    for c in ("success_umfe", "success_mfe_backtrack", "success_mfe_any"):
        assert not bad[c].any()
    assert all(math.isnan(x) for x in bad["best_ned"].to_list())
    for c in ("best_log10_p", "sequence", "evals_to_first", "seconds_to_first"):
        assert bad[c].is_null().all()
    # every other unit is untouched
    rest = lambda f: f.filter(~((pl.col("target_id") == "toy:a") & (pl.col("seed") == 0))).drop("errored", strict=False)
    assert rest(after).sort(["target_id", "seed", "wall_s"]).equals(rest(before).sort(["target_id", "seed", "wall_s"]))
    # downstream figures see it as unsolved: toy:a loses one of its two solved seeds
    solved_mean = lambda u: final_report.solved_counts(u, 128).to_dicts()[0]["solved_mean_over_seeds"]
    assert solved_mean(after) == solved_mean(before) - 0.5


def test_pre_fix_units_are_found_until_replaced(tmp_path):
    fix = {"margin_s": 60, "desirna": {"time": "2026-09-27T19:45:05+00:00"}}
    units = tmp_path / "units" / "desirna"
    units.mkdir(parents=True)
    (units / "p1__seed0.json").write_text(json.dumps({"started_utc": "2026-09-27T19:46:00+00:00"}))  # within margin
    (units / "p2__seed0.json").write_text(json.dumps({"started_utc": "2026-09-27T19:47:00+00:00"}))  # after
    assert final_report.pre_fix_units(tmp_path, fix) == ["desirna/p1__seed0"]
    (units / "p1__seed0.json").write_text(json.dumps({"started_utc": "2026-09-28T03:00:00+00:00"}))  # rerun
    assert final_report.pre_fix_units(tmp_path, fix) == []


def test_earlier_reports_are_archived_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(final_report, "REPO_ROOT", tmp_path)
    old = tmp_path / "final_v2_report.json"
    old.write_text(json.dumps({"audit": {"eterna100_v2": {"validation": {"valid": 29, "missing": 2371}}}, "sets": {}}))
    interim = tmp_path / "final_v2_report_INTERIM.json"
    interim.write_text(json.dumps({"status": "INTERIM (incomplete benchmark)", "audit": {}}))
    content = old.read_bytes()
    moved = final_report.archive_previous([old, interim, tmp_path / "absent.json"], tmp_path / "history")
    assert not old.exists() and not interim.exists() and len(moved) == 2
    assert moved[0]["status"].startswith("UNLABELLED") and moved[0]["coverage"]["eterna100_v2"]["valid"] == 29
    assert moved[1]["status"].startswith("INTERIM")
    assert (tmp_path / moved[0]["archived_to"]).read_bytes() == content          # kept byte for byte
    assert (tmp_path / "history" / "README.txt").exists()
    old.write_text("{}")                                                         # a second earlier file, same stamp
    import os
    os.utime(old, (0, (tmp_path / moved[0]["archived_to"]).stat().st_mtime))
    again = final_report.archive_previous([old], tmp_path / "history")
    assert again[0]["archived_to"] != moved[0]["archived_to"]                   # never clobbers the archive


def test_out_writes_a_copy_and_never_touches_the_canonical_report(tmp_path, monkeypatch):
    canonical = tmp_path / "final_v2_report.json"
    canonical.write_text('{"status": "FINAL", "canonical": true}')
    (tmp_path / "final_v2_retry.done").write_text("RETRY_DONE")
    monkeypatch.setattr(final_report, "PILOT_DIR", tmp_path)
    monkeypatch.setattr(final_report, "RETRY_DONE", tmp_path / "final_v2_retry.done")
    monkeypatch.setattr(final_report, "HISTORY", tmp_path / "report_history")
    monkeypatch.setattr(final_report, "SETS", ())                 # no runs: coverage trivially complete
    copy = tmp_path / "elsewhere" / "regenerated.json"
    copy.parent.mkdir()
    monkeypatch.setattr(sys, "argv", ["final_report.py", "--out", str(copy)])
    final_report.main()
    out = json.loads(copy.read_text())
    assert out["status"] == "FINAL" and "regenerated_copy" in out and "supersedes" not in out
    assert json.loads(canonical.read_text()) == {"status": "FINAL", "canonical": True}
    assert not (tmp_path / "report_history").exists()
