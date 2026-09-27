"""Resumable pilot runs: atomic unit files, resume validation, caps, errors, confirmation looks, summaries."""

import json
import time

import pytest

from ribomamba.design import runner, summary
from ribomamba.design.search import Evaluator

MANIFEST = {"name": "toy", "content_sha256": "0" * 64}
TARGETS = [{"id": "toy:a", "structure": "((((....))))"}, {"id": "toy:b", "structure": "((((....))))..(((...)))"}]
METHODS = ["random_pairs", "feedback_pair_edits"]


def config(budget=12, methods=METHODS, seeds=(0, 1)):
    return runner.make_config(MANIFEST, "toy", TARGETS, methods, list(seeds), budget)


def quiet(*args):
    pass


def test_run_writes_valid_units_and_resume_skips_them(tmp_path):
    cfg = config()
    counts = runner.run(tmp_path, cfg, TARGETS, workers=1, progress=quiet)
    assert counts == {"skipped_complete": 0, "complete": 8}
    for m in METHODS:
        for t in TARGETS:
            for seed in (0, 1):
                key = runner.unit_key(m, t["id"], seed)
                assert runner.validate_unit(tmp_path, key, cfg["config_hash"], 12) is None
                status = json.loads(runner.unit_paths(tmp_path, key)[1].read_text())
                assert status["status"] == "complete" and status["n_rows"] == 12
                assert status["oracle_calls"]["pf"] == status["cache_misses"]
    assert runner.run(tmp_path, cfg, TARGETS, workers=1, progress=quiet) == {"skipped_complete": 8}
    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert [e["event"] for e in events] == ["start", "stop", "start", "stop"]
    assert events[0]["max_hours"] is None  # no implicit user compute cap


def test_a_damaged_unit_is_detected_and_only_it_reruns(tmp_path):
    cfg = config()
    runner.run(tmp_path, cfg, TARGETS, workers=1, progress=quiet)
    key = runner.unit_key("random_pairs", "toy:b", 1)
    trace = runner.unit_paths(tmp_path, key)[0]
    trace.write_bytes(trace.read_bytes()[:-10])                  # a truncated file
    assert runner.validate_unit(tmp_path, key, cfg["config_hash"], 12) == "trace missing or hash differs"
    other = runner.unit_key("random_pairs", "toy:a", 0)
    runner.unit_paths(tmp_path, other)[1].unlink()              # a unit whose status never got written
    assert runner.validate_unit(tmp_path, other, cfg["config_hash"], 12) == "missing"
    counts = runner.run(tmp_path, cfg, TARGETS, workers=1, progress=quiet)
    assert counts == {"skipped_complete": 6, "complete": 2}
    assert runner.validate_unit(tmp_path, key, cfg["config_hash"], 12) is None


def test_a_different_configuration_is_refused(tmp_path):
    runner.run(tmp_path, config(), TARGETS, workers=1, progress=quiet)
    with pytest.raises(ValueError, match="different configuration"):
        runner.run(tmp_path, config(budget=13), TARGETS, workers=1, progress=quiet)


def test_errors_are_kept_and_capped_units_rerun(tmp_path, monkeypatch):
    def broken(target, seed, evaluate, settings):
        evaluate("A" * len(target))
        raise RuntimeError("deliberate failure")

    def slow(target, seed, evaluate, settings):
        while True:
            evaluate("A" * len(target))
            time.sleep(0.05)
    for name, fn in (("broken", broken), ("slow", slow)):
        monkeypatch.setitem(runner.METHODS, name, fn)
        monkeypatch.setitem(runner.METHOD_SETTINGS, name, {})

    cfg = config(budget=500, methods=["broken"], seeds=[0])
    assert runner.run(tmp_path / "e", cfg, TARGETS, workers=1, progress=quiet) == {"skipped_complete": 0, "error": 2}
    key = runner.unit_key("broken", "toy:a", 0)
    err = json.loads(runner.unit_paths(tmp_path / "e", key)[1].read_text())
    assert "deliberate failure" in err["reason"] and err["n_rows"] == 1      # the partial trace is kept
    assert runner.validate_unit(tmp_path / "e", key, cfg["config_hash"], 500) is None      # terminal: kept
    assert runner.validate_unit(tmp_path / "e", key, cfg["config_hash"], 500, retry_errors=True) == "retrying error"
    assert runner.run(tmp_path / "e", cfg, TARGETS, workers=1, progress=quiet) == {"skipped_complete": 2}

    cfg = config(budget=500, methods=["slow"], seeds=[0])
    counts = runner.run(tmp_path / "c", cfg, TARGETS, workers=1, max_hours=0.3 / 3600, progress=quiet)
    assert counts == {"skipped_complete": 0, "capped": 1, "not_started": 1}   # the longer target runs first
    capped = runner.unit_key("slow", "toy:b", 0)
    status = json.loads(runner.unit_paths(tmp_path / "c", capped)[1].read_text())
    assert status["status"] == "capped" and 0 < status["n_rows"] < 500
    assert runner.validate_unit(tmp_path / "c", capped, cfg["config_hash"], 500) == "status capped"
    assert runner.validate_unit(tmp_path / "c", runner.unit_key("slow", "toy:a", 0), cfg["config_hash"], 500) == "missing"


def test_confirmation_looks_need_a_label_and_are_logged(tmp_path):
    cfg = config()
    log = tmp_path / "looks.jsonl"
    with pytest.raises(PermissionError):
        runner.log_confirmation_look("r", "confirmation", "", cfg, log)
    runner.log_confirmation_look("r", "confirmation", "rev-1", cfg, log)
    runner.log_confirmation_look("r", "all", "rev-2", cfg, log)
    looks = [json.loads(line) for line in log.read_text().splitlines()]
    assert [x["label"] for x in looks] == ["rev-1", "rev-2"] and looks[0]["config_hash"] == cfg["config_hash"]


def test_summary_checkpoints_are_prefixes_of_the_trace(tmp_path):
    cfg = config()
    runner.run(tmp_path, cfg, TARGETS, workers=1, progress=quiet)
    _, statuses, cp = summary.checkpoints(tmp_path, budgets=(4, 12))
    assert cp.height == 16 and set(cp["budget"].to_list()) == {4, 12}
    wide = cp.pivot(on="budget", index=["method", "target_id", "seed"], values="best_ned")
    assert (wide["12"] <= wide["4"]).all()                       # best-so-far can only improve
    agg = summary.aggregate(cp)
    assert {r["targets"] for r in agg} == {2}
    diff = summary.paired(cp, "feedback_pair_edits", "random_pairs", "best_ned", 12)
    assert diff["n_targets"] == 2


def test_evaluator_rows_match_the_trace_schema():
    ev = Evaluator(runner.Target("toy:a", "((((....))))"), budget=2)
    ev("GGGGAAAACCCC")
    extra = set(ev.rows[0]) - set(runner.SCHEMA)
    missing = set(runner.SCHEMA) - set(ev.rows[0]) - {"method", "target_id", "seed"}
    assert not extra and not missing
