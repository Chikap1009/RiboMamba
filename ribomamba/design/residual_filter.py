"""Online competition-residual filter for SAMFEO's mutations (frozen models only).

For a parent P and its K children, rank by a + c_hat, where a = -Delta E_target/RT is
exact and c_hat estimates the rival-only term -Delta ln Z_rest
(docs/experiments/2026-09-27-competition-residual.md). Per DISTINCT parent (cached):
a rival bank drawn from its Boltzmann ensemble (siblings.rival_bank: 1 MFE, 1 partition
function, 200 stochastic backtracks) and its rival energies. Per child: its target
energy and every rival's energy where formable. All of these are counted as the
method's own calls (evaluate.internal); their time and the model's is model_wall_s.
The parent's ln P is SAMFEO's own objective value for that sequence (read from the
harness cache, where it is identical: tests/test_design_baselines.py).

Model files: JSON {"kind": "ridge", "features", "w", "mu", "sd"} or a torch file
{"kind": "mlp", "features", "state", "mu", "sd", "hidden"}; "physics:bank" uses
c_hat = c_bank with no learning.
"""

import json
import math
import time
from collections import OrderedDict

import numpy as np
import RNA

from ribomamba.design.residual_models import child_features
from ribomamba.design.scoring import KT, unformable_pairs
from ribomamba.design.siblings import rival_bank, rival_energies
from ribomamba.eval.folding import model_details, pair_table

BANK_CACHE = 256


class ResidualScorer:
    def __init__(self, path: str):
        self.kind, self.model = "bank", None
        if not path.endswith("physics:bank"):
            if path.endswith(".json"):
                m = json.loads(open(path).read())
                self.kind, self.features = "ridge", m["features"]
                self.w, self.mu, self.sd = np.array(m["w"]), np.array(m["mu"]), np.array(m["sd"])
            else:
                import torch
                m = torch.load(path, map_location="cpu", weights_only=False)
                self.kind, self.features = "mlp", m["features"]
                net = torch.nn.Sequential(torch.nn.Linear(len(m["features"]), m["hidden"]), torch.nn.GELU(),
                                          torch.nn.Linear(m["hidden"], m["hidden"]), torch.nn.GELU(),
                                          torch.nn.Linear(m["hidden"], 1))
                net.load_state_dict(m["state"])
                self.net, self.mu, self.sd = net.eval(), np.array(m["mu"]), np.array(m["sd"])
        self.banks: OrderedDict = OrderedDict()

    def _bank(self, target, parent: str, evaluate):
        if parent in self.banks:
            self.banks.move_to_end(parent)
            return self.banks[parent]
        seed = int.from_bytes(parent.encode()[:8].ljust(8, b"\0"), "little") % (2**31 - 1)
        rivals, cost = rival_bank(parent, target.structure, seed=seed)
        evaluate.internal.mfe += cost["mfe"]
        evaluate.internal.pf += cost["pf"]
        evaluate.internal.eval += cost["eval"]
        pts = [pair_table(r) for r in rivals]
        energies = rival_energies(parent, rivals, pts)
        e_target = RNA.fold_compound(parent, model_details()).eval_structure(target.structure)
        evaluate.internal.eval += len(rivals) + 1
        self.banks[parent] = (rivals, pts, energies, e_target)
        if len(self.banks) > BANK_CACHE:
            self.banks.popitem(last=False)
        return self.banks[parent]

    def __call__(self, target, parent: str, children: list[str], defect_list, evaluate) -> list[float]:
        start = time.perf_counter()
        rivals, pts, parent_rivals, e_parent = self._bank(target, parent, evaluate)
        cached = evaluate.cache.get(parent)
        parent_ln_p = cached.log_p_target if cached is not None else math.nan
        rows, a_list = [], []
        md = model_details()
        for child in children:
            e_child = RNA.fold_compound(child, md).eval_structure(target.structure)
            energies = rival_energies(child, rivals, pts)
            evaluate.internal.eval += 1 + len(rivals)
            a = -(e_child - e_parent) / KT
            a_list.append(a)
            rows.append(child_features(target.structure, parent, child, defect_list, parent_ln_p, a,
                                       parent_rivals, energies))
        a = np.array(a_list)
        if self.kind == "bank":
            c_hat = np.array([r["c_bank_filled"] for r in rows])
        else:
            X = np.array([[r[f] for f in self.features] for r in rows], dtype=float)
            if self.kind == "ridge":
                c_hat = np.c_[np.ones(len(X)), (X - self.mu) / self.sd] @ self.w
            else:
                import torch
                with torch.no_grad():
                    c_hat = self.net(torch.tensor((X - self.mu) / self.sd, dtype=torch.float32)).squeeze(-1).numpy()
        evaluate.model_calls += 1
        evaluate.model_wall_s += time.perf_counter() - start
        return list(-(a + c_hat))


class SiblingScorer(ResidualScorer):
    """Online scorer for the sibling-trained per-position critics (residual_critic.py).

    generic: rank by y_hat; norival / rival: rank by a + c_hat. Rival banks are drawn only
    for the rival variant (the others pay no bank cost). Encoding, GPU transfer and
    inference time are counted in model_wall_s; folds and evaluations in evaluate.internal.
    """

    def __init__(self, path: str):
        import torch

        from ribomamba.design.critic import CriticConfig
        from ribomamba.design.residual_critic import SiblingCritic
        state = torch.load(path, map_location="cpu", weights_only=False)
        self.variant = state["variant"]
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SiblingCritic(CriticConfig(**state["config"]), use_rivals=self.variant == "rival")
        self.model.load_state_dict(state["state"])
        self.model = self.model.to(self.device).eval()
        self.banks = OrderedDict()
        self.pt_cache: dict = {}

    def __call__(self, target, parent: str, children: list[str], defect_list, evaluate) -> list[float]:
        import torch

        from ribomamba.design.residual_critic import collate_sibling, encode_sibling
        start = time.perf_counter()
        md = model_details()
        if self.variant == "rival":
            rivals, pts, parent_rivals, e_parent = self._bank(target, parent, evaluate)
        else:
            rivals, pts, parent_rivals = [], [], np.zeros(0)
            e_parent = RNA.fold_compound(parent, md).eval_structure(target.structure)
            evaluate.internal.eval += 1
        cached = evaluate.cache.get(parent)
        parent_ln_p = cached.log_p_target if cached is not None else math.nan
        rows, a_list = [], []
        for child in children:
            e_child = RNA.fold_compound(child, md).eval_structure(target.structure)
            energies = rival_energies(child, rivals, pts) if rivals else np.zeros(0)
            evaluate.internal.eval += 1 + len(rivals)
            a = -(e_child - e_parent) / KT
            a_list.append(a)
            rows.append({"structure": target.structure, "parent": parent, "child": child,
                         "parent_defect": list(defect_list), "target_energy": e_child, "parent_target_energy": e_parent,
                         "parent_ln_p": parent_ln_p, "a": a, "rivals": rivals,
                         "parent_rival_energy": list(parent_rivals), "rival_energy": list(energies)})
        batch = collate_sibling([encode_sibling(r, self.variant, self.pt_cache) for r in rows], self.device)
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=self.device == "cuda"):
            out = self.model(batch).float().cpu().numpy()
        score = out if self.variant == "generic" else np.array(a_list) + out
        evaluate.model_calls += 1
        evaluate.model_wall_s += time.perf_counter() - start
        return list(-score)
