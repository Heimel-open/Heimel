"""
mecha_checker.py — Bounded model checker for MECHA (EFAVΛLΦ_Epistemic)

Python BFS implementation of the TLA+ bounded model.
Matches EFAVΛLΦ_Epistemic.tla / EFAVΛLΦ_Epistemic.cfg:
  Operators = {"op1", "op2"}, MaxTime = 3

Invariants checked at every reachable state:
  1. ConjunctiveIntegrity — no ALLOW without M ∧ E ∧ H ∧ A
  2. SeparationOfDuties   — requester ≠ authorizer
  3. NoDoubleFinalize     — ¬(executed ∧ vetoed)

Usage:
    python mecha_checker.py
    python mecha_checker.py --bug      # simulate v1.0 bug (missing ~vetoed guard)
"""

import argparse
import json
import logging
import os
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional

# ── Constants ─────────────────────────────────────────────────────────────────
OPERATORS = ("op1", "op2")
MAX_TIME = 3

logging.basicConfig(
    format="[%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("mecha")


# ── State representation ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class HumanState:
    acuity: int   # 0..5
    cog_load: int # 0..5
    aff_bias: int # 0..5

    def is_capable(self) -> bool:
        return (
            self.acuity <= 3
            and self.cog_load <= 2
            and self.aff_bias <= 2
            and (self.acuity + self.cog_load + self.aff_bias) <= 7
        )


# Two discrete human states: Capable (baseline) and Incapable (degraded)
HUMAN_CAPABLE   = HumanState(acuity=1, cog_load=1, aff_bias=1)
HUMAN_INCAPABLE = HumanState(acuity=4, cog_load=3, aff_bias=3)


@dataclass(frozen=True)
class State:
    machine:    Tuple[str, ...]          # ("Ready"|"Unstable") per op
    evidence:   Tuple[str, ...]          # ("Verified"|"Unverified") per op
    human:      Tuple[HumanState, ...]   # HumanState per op
    authority:  Tuple[str, ...]          # ("Authorized"|"Unauthorized") per op
    executed:   Tuple[bool, ...]         # action_executed per op
    vetoed:     Tuple[bool, ...]         # vetoed per op
    authorizers: Tuple[frozenset, ...]   # frozenset(Operators) per op
    sensor:     str                      # "Clean"|"Anomaly"
    time:       int


def initial_state() -> State:
    n = len(OPERATORS)
    return State(
        machine    = ("Ready",) * n,
        evidence   = ("Verified",) * n,
        human      = (HUMAN_CAPABLE,) * n,
        authority  = ("Authorized",) * n,
        executed   = (False,) * n,
        vetoed     = (False,) * n,
        authorizers= (frozenset(),) * n,
        sensor     = "Clean",
        time       = 0,
    )


def idx(op: str) -> int:
    return OPERATORS.index(op)


# ── Helper: replace one element in a tuple ───────────────────────────────────

def _r(tup: tuple, i: int, val) -> tuple:
    lst = list(tup)
    lst[i] = val
    return tuple(lst)


# ── Invariants ────────────────────────────────────────────────────────────────

def check_invariants(s: State) -> List[Tuple[str, bool, str]]:
    """Returns list of (invariant_name, passed, detail)."""
    results = []
    all_ok = True

    # ConjunctiveIntegrity
    ci_ok = True
    ci_detail = ""
    for op in OPERATORS:
        i = idx(op)
        if s.executed[i]:
            if not (
                s.machine[i] == "Ready"
                and s.evidence[i] == "Verified"
                and s.human[i].is_capable()
                and s.authority[i] == "Authorized"
            ):
                ci_ok = False
                ci_detail = f"ALLOW without full MECHA gate for {op}"
                all_ok = False
                break
    results.append(("ConjunctiveIntegrity", ci_ok, ci_detail or "OK"))

    # SeparationOfDuties
    sod_ok = True
    sod_detail = ""
    for op in OPERATORS:
        i = idx(op)
        if s.executed[i]:
            has_other = any(a != op for a in s.authorizers[i])
            if not has_other:
                sod_ok = False
                sod_detail = f"No distinct authorizer for {op}"
                all_ok = False
                break
    results.append(("SeparationOfDuties", sod_ok, sod_detail or "OK"))

    # NoDoubleFinalize
    ndf_ok = True
    ndf_detail = ""
    for op in OPERATORS:
        i = idx(op)
        if s.executed[i] and s.vetoed[i]:
            ndf_ok = False
            ndf_detail = f"Both executed AND vetoed for {op}"
            all_ok = False
            break
    results.append(("NoDoubleFinalize", ndf_ok, ndf_detail or "OK"))

    return results


# ── Transitions ───────────────────────────────────────────────────────────────

def transitions(s: State, bug_mode: bool = False) -> List[Tuple[str, State]]:
    """
    Generate all enabled next states from s.
    bug_mode=True omits the ~vetoed[op] guard from AllowAction (replicates v1.0 bug).
    """
    nexts = []

    # Tick
    if s.time < MAX_TIME:
        nexts.append(("Tick", State(**{**s.__dict__, "time": s.time + 1})))

    for op in OPERATORS:
        i = idx(op)

        # AddAuthorizer(op, auth)
        for auth in OPERATORS:
            if auth != op and auth not in s.authorizers[i]:
                new_auth = _r(s.authorizers, i, s.authorizers[i] | frozenset([auth]))
                nexts.append((f"AddAuth({op},{auth})", State(**{**s.__dict__, "authorizers": new_auth})))

        # AllowAction(op)
        gate = (
            not s.executed[i]
            and s.machine[i] == "Ready"
            and s.evidence[i] == "Verified"
            and s.human[i].is_capable()
            and s.authority[i] == "Authorized"
            and any(a != op for a in s.authorizers[i])
        )
        if bug_mode:
            # v1.0: missing ~vetoed[op] guard — can allow even when vetoed
            if gate:
                new_exec = _r(s.executed, i, True)
                nexts.append((f"Allow({op})", State(**{**s.__dict__, "executed": new_exec})))
        else:
            # v1.1: correct — requires ~vetoed[op]
            if gate and not s.vetoed[i]:
                new_exec = _r(s.executed, i, True)
                nexts.append((f"Allow({op})", State(**{**s.__dict__, "executed": new_exec})))

        # VetoAction(op)
        if not s.executed[i] and not s.vetoed[i]:
            new_vetoed = _r(s.vetoed, i, True)
            nexts.append((f"Veto({op})", State(**{**s.__dict__, "vetoed": new_vetoed})))

        # State degradation/recovery transitions only apply to non-executed operators.
        # Once AllowAction fires for op, that operator's state is frozen — the
        # execution-boundary decision has been made and cannot be retroactively
        # invalidated by subsequent environmental changes.
        if not s.executed[i]:
            if s.machine[i] == "Ready":
                nexts.append((f"DegradeMachine({op})", State(**{**s.__dict__, "machine": _r(s.machine, i, "Unstable")})))
            if s.machine[i] == "Unstable":
                nexts.append((f"RecoverMachine({op})", State(**{**s.__dict__, "machine": _r(s.machine, i, "Ready")})))

            if s.evidence[i] == "Verified":
                nexts.append((f"InvalidateEvidence({op})", State(**{**s.__dict__, "evidence": _r(s.evidence, i, "Unverified")})))

            if s.human[i].is_capable():
                nexts.append((f"DegradeHuman({op})", State(**{**s.__dict__, "human": _r(s.human, i, HUMAN_INCAPABLE)})))
            if not s.human[i].is_capable():
                nexts.append((f"RecoverHuman({op})", State(**{**s.__dict__, "human": _r(s.human, i, HUMAN_CAPABLE)})))

            if s.authority[i] == "Authorized":
                nexts.append((f"RevokeAuth({op})", State(**{**s.__dict__, "authority": _r(s.authority, i, "Unauthorized")})))

    return nexts


# ── BFS model checker ─────────────────────────────────────────────────────────

def run_model_check(bug_mode: bool = False) -> Dict[str, Any]:
    """
    BFS over the reachable state space.
    Returns summary dict with all results and per-state history for visualization.
    """
    label = "v1.0 (BUG)" if bug_mode else "v1.1 (CORRECT)"
    log.info(f"Starting MECHA bounded model check — {label}")
    log.info(f"Operators={OPERATORS}, MaxTime={MAX_TIME}")

    init = initial_state()
    visited: dict = {init: 0}   # state -> BFS level
    queue = deque([(init, 0)])

    violations: List[Dict] = []
    states_by_level: defaultdict = defaultdict(int)
    states_by_level[0] = 1

    invariant_stats = {"ConjunctiveIntegrity": 0, "SeparationOfDuties": 0, "NoDoubleFinalize": 0}
    total_checks = 0
    allow_states = 0

    history = []   # for per-state logging / visualization

    while queue:
        s, level = queue.popleft()
        inv_results = check_invariants(s)
        total_checks += 1

        any_executed = any(s.executed)
        if any_executed:
            allow_states += 1

        state_ok = True
        for name, passed, detail in inv_results:
            if not passed:
                state_ok = False
                invariant_stats[name] += 1
                v = {
                    "level": level,
                    "invariant": name,
                    "detail": detail,
                    "state_summary": _state_summary(s),
                }
                violations.append(v)
                log.error(f"VIOLATION at BFS level {level}: {name} — {detail}")

        history.append({
            "level": level,
            "states_at_level": states_by_level[level],
            "any_executed": any_executed,
            "ok": state_ok,
        })

        for action_name, ns in transitions(s, bug_mode=bug_mode):
            if ns not in visited:
                visited[ns] = level + 1
                states_by_level[level + 1] += 1
                queue.append((ns, level + 1))

    total_states = len(visited)
    max_level = max(states_by_level.keys())

    log.info(f"States explored:  {total_states}")
    log.info(f"Max BFS depth:    {max_level}")
    log.info(f"States with ALLOW:{allow_states}")
    log.info(f"Total violations: {len(violations)}")

    for inv_name, count in invariant_stats.items():
        status = "VIOLATED" if count > 0 else "HOLDS"
        log.info(f"  {inv_name}: {status} ({count} violations)")

    return {
        "label": label,
        "bug_mode": bug_mode,
        "total_states": total_states,
        "max_level": max_level,
        "allow_states": allow_states,
        "violations": violations,
        "invariant_stats": invariant_stats,
        "states_by_level": dict(states_by_level),
        "history": history,
    }


def _state_summary(s: State) -> dict:
    return {
        "machine":   list(s.machine),
        "evidence":  list(s.evidence),
        "human_capable": [h.is_capable() for h in s.human],
        "authority": list(s.authority),
        "executed":  list(s.executed),
        "vetoed":    list(s.vetoed),
        "authorizers": [list(a) for a in s.authorizers],
        "time":      s.time,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MECHA Bounded Model Checker")
    parser.add_argument("--bug", action="store_true",
                        help="Run v1.0 bug mode (missing ~vetoed guard in AllowAction)")
    args = parser.parse_args()

    results = run_model_check(bug_mode=args.bug)

    os.makedirs("results", exist_ok=True)
    out_label = "bug" if args.bug else "correct"
    out_path = f"results/mecha_{out_label}.json"
    with open(out_path, "w") as f:
        # history is large; summarize levels only for JSON output
        results_out = dict(results)
        results_out["history"] = f"[{len(results['history'])} state records — see Python object]"
        json.dump(results_out, f, indent=2, default=str)

    print(f"\nResultat lagret: {out_path}")
    print(f"  Stater utforsket:  {results['total_states']}")
    print(f"  Brudd på invarianter: {len(results['violations'])}")
    if results["violations"]:
        print(f"\n  FEIL: {results['violations'][0]['invariant']} — {results['violations'][0]['detail']}")
    else:
        print("  Alle invarianter holder. ✅")


if __name__ == "__main__":
    main()
