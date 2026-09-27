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
