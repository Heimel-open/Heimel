#!/usr/bin/env python3
"""TOFOO relational emergence falsification harness v2.

V2 tests distributed latent-rule induction rather than graph aggregation.
No single participant shard uniquely identifies the latent rules. The full
cross-participant evidence does. A governed relational field may accumulate
locally-supported hypotheses and admit a rule only when all participants have
independently supported the same hypothesis with valid local provenance.

Primary metric (signal-discovery only):
    relational_rule_accuracy - max(
        isolated_max,
        pooled_raw,
        structured_raw,
        pooled_iterative,
    )

A positive run is not a research claim until reproduced across seeds/models
with budget normalization and independent replication.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from itertools import product, combinations
import argparse
import gc
import json
import random
import re
import sys
from typing import Dict, Iterable, List, Tuple


RULES: Dict[str, Tuple[int, ...]] = {
    "IDENTITY": (0, 1, 2, 3, 4),
    "REVERSE": (4, 3, 2, 1, 0),
    "ROTL1": (1, 2, 3, 4, 0),
    "ROTR1": (4, 0, 1, 2, 3),
    "SWAP12": (1, 0, 2, 3, 4),
    "SWAP45": (0, 1, 2, 4, 3),
    "PAIRSWAP": (1, 0, 3, 2, 4),
    "EVENS_FIRST": (0, 2, 4, 1, 3),
}

RULE_CATALOG = "\n".join(
    f"- {name}: output positions " + " ".join(str(i + 1) for i in perm)
    for name, perm in RULES.items()
)


@dataclass(frozen=True)
class Evidence:
    eid: str
    operator: str
    inp: str
    out: str
    participant: int


@dataclass(frozen=True)
class TransferQuery:
    qid: str
    first_operator: str
    second_operator: str
    inp: str
    expected: str


@dataclass
class World:
    wid: str
    operators: List[str]
    truth: Dict[str, str]
    shards: List[List[Evidence]]
    transfer: List[TransferQuery]


def apply_rule(seq: str, rule_name: str) -> str:
    return "".join(seq[i] for i in RULES[rule_name])


def compatible_rules(e: Evidence) -> set[str]:
    return {name for name in RULES if apply_rule(e.inp, name) == e.out}


def training_bank() -> List[str]:
    return [
        "".join(x)
        for x in product("ABC", repeat=5)
        if 2 <= len(set(x)) <= 3
    ]


def find_ambiguous_examples(rule_name: str, count: int, seed: int) -> List[Tuple[str, str]]:
    """Find examples individually ambiguous but jointly unique for rule_name."""
    r = random.Random(seed)
    candidates = []
    for inp in training_bank():
        out = apply_rule(inp, rule_name)
        fake = Evidence("tmp", "OP", inp, out, 0)
        comp = compatible_rules(fake)
        if rule_name in comp and len(comp) >= 2:
            candidates.append((inp, out, comp))
    r.shuffle(candidates)

    for pool in (candidates[:120], candidates):
        for combo in combinations(pool, count):
            inter = set(RULES)
            for _, _, comp in combo:
                inter &= comp
            if inter == {rule_name}:
                return [(inp, out) for inp, out, _ in combo]
    raise RuntimeError(f"Could not construct ambiguous evidence for {rule_name}")


def make_world(seed: int, wid: str, participants: int = 3, operator_count: int = 3) -> World:
    if participants < 2:
        raise ValueError("participants must be >= 2")
    if operator_count < 2 or operator_count > 4:
        raise ValueError("operator_count must be 2..4")

    r = random.Random(seed)
    operator_names = ["KEM", "RIV", "TOV", "SUL"][:operator_count]
    chosen_rules = r.sample(list(RULES), operator_count)
    truth = dict(zip(operator_names, chosen_rules))
    shards: List[List[Evidence]] = [[] for _ in range(participants)]

    for oi, op in enumerate(operator_names):
        examples = find_ambiguous_examples(truth[op], participants, seed + 1009 * (oi + 1))
        for p, (inp, out) in enumerate(examples):
            shards[p].append(Evidence(f"{wid}-{op}-P{p}", op, inp, out, p))

    for p, shard in enumerate(shards):
        random.Random(seed + 7919 + p).shuffle(shard)

    for op in operator_names:
        local_sets = []
        for p in range(participants):
            e = next(x for x in shards[p] if x.operator == op)
            comp = compatible_rules(e)
            if len(comp) < 2:
                raise AssertionError(f"Local evidence unexpectedly unique: {wid} {op} P{p}")
            local_sets.append(comp)
        inter = set(RULES)
        for s in local_sets:
            inter &= s
        if inter != {truth[op]}:
            raise AssertionError(f"Joint evidence not uniquely identifying: {wid} {op} {inter}")

    transfer = []
    distinct_inputs = ["ABCDE", "BCDEA", "CDEAB", "DEABC"]
    for qi in range(min(4, operator_count + 1)):
        a = operator_names[qi % operator_count]
        b = operator_names[(qi + 1) % operator_count]
        inp = distinct_inputs[qi]
        expected = apply_rule(apply_rule(inp, truth[a]), truth[b])
        transfer.append(TransferQuery(f"{wid}-T{qi}", a, b, inp, expected))

    return World(wid, operator_names, truth, shards, transfer)


def evidence_text(shard: List[Evidence]) -> str:
    return "\n".join(
        f"[{e.eid}] operator={e.operator} input={e.inp} output={e.out}"
        for e in shard
    )


def pooled_text(world: World) -> str:
    rows = [e for shard in world.shards for e in shard]
    random.Random(17 + sum(ord(c) for c in world.wid)).shuffle(rows)
    return evidence_text(rows)


def structured_text(world: World) -> str:
    lines = []
    for op in world.operators:
        lines.append(f"OPERATOR {op}")
        for p, shard in enumerate(world.shards):
            e = next(x for x in shard if x.operator == op)
            lines.append(f"  participant={p} [{e.eid}] input={e.inp} output={e.out}")
    return "\n".join(lines)


def field_new(world: World) -> dict:
    return {
        "operators": list(world.operators),
        "supports": {op: {rule: {} for rule in RULES} for op in world.operators},
        "admitted": {},
        "unresolved": {},
        "revision": 0,
        "attempts": 0,
        "mutations": 0,
    }


def field_text(field: dict) -> str:
    lines = ["GOVERNED RELATIONAL FIELD:"]
    for op in field["operators"]:
        if op in field["admitted"]:
            lines.append(f"- {op}: ADMITTED {field['admitted'][op]}")
            continue
        pending = []
        for rule, supporters in field["supports"][op].items():
            if supporters:
                ps = ",".join(str(x) for x in sorted(supporters))
                pending.append(f"{rule}[participants={ps}]")
        if pending:
            lines.append(f"- {op}: PENDING " + "; ".join(pending))
        else:
            lines.append(f"- {op}: PENDING NONE")
        if op in field["unresolved"]:
            lines.append(f"  unresolved={field['unresolved'][op]}")
    return "\n".join(lines)


def parse_hypotheses(raw: str, shard: List[Evidence], operators: Iterable[str]) -> List[Tuple[str, str, str]]:
    ops = set(operators)
    rules = set(RULES)
    eids = {e.eid for e in shard}
    parsed = []
    for line in raw.splitlines():
        up = line.upper()
        found_ops = [op for op in ops if re.search(rf"\b{re.escape(op)}\b", up)]
        found_rules = [rule for rule in rules if re.search(rf"\b{re.escape(rule)}\b", up)]
        found_eids = [eid for eid in eids if eid.upper() in up]
        if len(found_ops) == len(found_rules) == len(found_eids) == 1:
            item = (found_ops[0], found_rules[0], found_eids[0])
            if item not in parsed:
                parsed.append(item)
    return parsed


def parse_rules(raw: str, operators: Iterable[str]) -> Dict[str, str]:
    ops = list(operators)
    result = {}
    for line in raw.splitlines():
        up = line.upper()
        found_ops = [op for op in ops if re.search(rf"\b{re.escape(op)}\b", up)]
        found_rules = [rule for rule in RULES if re.search(rf"\b{re.escape(rule)}\b", up)]
        if len(found_ops) == 1 and len(found_rules) == 1 and found_ops[0] not in result:
            result[found_ops[0]] = found_rules[0]
    return result


def recompute_admission(field: dict, participants: int) -> bool:
    changed = False
    for op in field["operators"]:
        fully_supported = [
            rule for rule, supporters in field["supports"][op].items()
            if len(supporters) == participants
        ]
        if len(fully_supported) == 1:
            rule = fully_supported[0]
            if field["admitted"].get(op) != rule:
                field["admitted"][op] = rule
                field["unresolved"].pop(op, None)
                changed = True
        elif len(fully_supported) > 1:
            val = sorted(fully_supported)
            if field["unresolved"].get(op) != val:
                field["unresolved"][op] = val
                changed = True
    return changed


def admit_hypotheses(world: World, field: dict, shard: List[Evidence], participant: int,
                     round_id: int, hypotheses: List[Tuple[str, str, str]]) -> List[dict]:
    """Only function allowed to mutate governed relational state."""
    field["attempts"] += 1
    events = []
    local = {e.eid: e for e in shard}
    mutated = False

    if not hypotheses:
        return [{"participant": participant, "round": round_id, "decision": "NO_CANDIDATE"}]

    for op, rule, eid in hypotheses:
        event = {"participant": participant, "round": round_id, "operator": op,
                 "rule": rule, "evidence_id": eid}
        e = local.get(eid)
        if e is None:
            event.update(decision="REJECT", basis="NONLOCAL_PROVENANCE")
            events.append(event)
            continue
        if e.operator != op:
            event.update(decision="REJECT", basis="PROVENANCE_OPERATOR_MISMATCH")
            events.append(event)
            continue
        if rule not in RULES:
            event.update(decision="REJECT", basis="UNKNOWN_RULE")
            events.append(event)
            continue
        if apply_rule(e.inp, rule) != e.out:
            event.update(decision="REJECT", basis="LOCAL_EVIDENCE_CONTRADICTS_RULE")
            events.append(event)
            continue

        supporters = field["supports"][op][rule]
        if participant not in supporters:
            supporters[participant] = eid
            mutated = True
        event.update(decision="SUPPORT", basis="LOCAL_PROVENANCE_VERIFIED")
        events.append(event)

    if recompute_admission(field, len(world.shards)):
        mutated = True
    if mutated:
        field["revision"] += 1
        field["mutations"] += 1
    return events


def participant_prompt(world: World, shard: List[Evidence], field: dict, round_id: int) -> str:
    return f"""You are one participant in a distributed latent-rule experiment.
Your job is to propose rule hypotheses using only YOUR EVIDENCE plus the current governed field.

Each rule is a position permutation over a five-character input. The catalog is:
{RULE_CATALOG}

Important:
- Your local example may be ambiguous. That is intentional.
- Prefer PENDING rules from the field when compatible with your own local example.
- If no pending rule is compatible, propose other compatible catalog rules.
- Cite exactly the local evidence id that supports each hypothesis.
- Do not cite another participant's evidence id.
- Do not invent rule names or evidence ids.
- Return one line for EVERY catalog rule compatible with each local example.
- It is correct to return multiple hypotheses for the same operator because local evidence is intentionally ambiguous.
  Example FORMAT ONLY: HYP <operator> <rule_name> <local_evidence_id>

ROUND: {round_id}
YOUR EVIDENCE:
{evidence_text(shard)}

{field_text(field)}
"""


def direct_prompt(context: str, operators: List[str], prior: Dict[str, str] | None = None) -> str:
    prior_text = "NONE" if not prior else "\n".join(f"- {op}: {rule}" for op, rule in prior.items())
    return f"""Infer the latent rule for each operator from the supplied training examples.
Each rule is a position permutation over a five-character input.

RULE CATALOG:
{RULE_CATALOG}

Return one line per operator with the operator and one catalog rule name.
Example FORMAT ONLY: RULE <operator> <rule_name>
Do not invent rule names.

OPERATORS: {', '.join(operators)}
CURRENT GUESSES (may be revised):
{prior_text}

TRAINING EVIDENCE:
{context}
"""


def mapping_accuracy(pred: Dict[str, str], truth: Dict[str, str]) -> float:
    return sum(pred.get(op) == rule for op, rule in truth.items()) / len(truth)


def transfer_accuracy(pred: Dict[str, str], queries: List[TransferQuery]) -> float:
    correct = 0
    for q in queries:
        a = pred.get(q.first_operator)
        b = pred.get(q.second_operator)
        if a is None or b is None:
            continue
        got = apply_rule(apply_rule(q.inp, a), b)
        correct += got == q.expected
    return correct / len(queries)


def oracle_mapping(world: World) -> Dict[str, str]:
    result = {}
    for op in world.operators:
        possible = set(RULES)
        for shard in world.shards:
            e = next(x for x in shard if x.operator == op)
            possible &= compatible_rules(e)
        if len(possible) != 1:
            raise AssertionError(f"Oracle intersection not unique for {world.wid}/{op}: {possible}")
        result[op] = next(iter(possible))
    return result


class Runner:
    def __init__(self, mock: bool = False, use_4bit: bool = True, max_new_tokens: int = 160):
        self.mock = mock
        self.use_4bit = use_4bit
        self.max_new_tokens = max_new_tokens
        self.model = None
        self.tokenizer = None
        self.model_id = None
        self.calls = 0
        self.input_tokens = 0
        self.output_chars = 0

    def unload(self):
        self.model = self.tokenizer = self.model_id = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def load(self, model_id: str):
        if self.mock:
            self.model_id = "MOCK"
            return
        if self.model_id == model_id and self.model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.unload()
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        kwargs = {"device_map": "auto", "low_cpu_mem_usage": True}
        if self.use_4bit and torch.cuda.is_available():
            from transformers import BitsAndBytesConfig
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
            )
        else:
            kwargs["torch_dtype"] = torch.float16 if torch.cuda.is_available() else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
        self.model_id = model_id

    def tokens(self, text: str) -> int:
        if self.mock or self.tokenizer is None:
            return max(1, len(text) // 4)
        return len(self.tokenizer.encode(text))

    def run(self, prompt: str, model_id: str, max_new_tokens: int | None = None) -> str:
        self.load(model_id)
        self.calls += 1
        self.input_tokens += self.tokens(prompt)
        if self.mock:
            if "YOUR EVIDENCE:" in prompt and "GOVERNED RELATIONAL FIELD:" in prompt:
                ev = re.findall(r"\[([^\]]+)\] operator=([A-Z]+) input=([A-Z]+) output=([A-Z]+)", prompt)
                lines = []
                for eid, op, inp, out in ev:
                    compatible = [r for r in RULES if apply_rule(inp, r) == out]
                    for choice in compatible:
                        lines.append(f"HYP {op} {choice} {eid}")
                raw = "\n".join(lines)
                self.output_chars += len(raw)
                return raw

            examples = []
            current_op = None
            for line in prompt.splitlines():
                m = re.match(r"OPERATOR\s+([A-Z]+)", line.strip())
                if m:
                    current_op = m.group(1)
                    continue
                m = re.search(r"\[([^\]]+)\]\s+operator=([A-Z]+)\s+input=([A-Z]+)\s+output=([A-Z]+)", line)
                if m:
                    examples.append((m.group(2), m.group(3), m.group(4)))
                    continue
                m = re.search(r"\[([^\]]+)\]\s+input=([A-Z]+)\s+output=([A-Z]+)", line)
                if m and current_op:
                    examples.append((current_op, m.group(2), m.group(3)))
            ops_match = re.search(r"OPERATORS:\s*([^\n]+)", prompt)
            if ops_match:
                ops = [x.strip() for x in ops_match.group(1).split(",")]
                lines = []
                for op in ops:
                    poss = set(RULES)
                    found = False
                    for eop, inp, out in examples:
                        if eop == op:
                            found = True
                            poss &= {r for r in RULES if apply_rule(inp, r) == out}
                    if found and len(poss) == 1:
                        lines.append(f"RULE {op} {next(iter(poss))}")
                    elif found:
                        lines.append(f"RULE {op} {sorted(poss)[0]}")
                raw = "\n".join(lines)
                self.output_chars += len(raw)
                return raw
            return ""

        import torch
        text = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.tokenizer(text, return_tensors="pt")
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens or self.max_new_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        raw = self.tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        self.output_chars += len(raw)
        return raw


def selfcheck() -> dict:
    w = make_world(20260819, "SELF", participants=3, operator_count=3)
    assert oracle_mapping(w) == w.truth
    assert all(len(compatible_rules(e)) >= 2 for shard in w.shards for e in shard)

    shard = w.shards[0]
    e = shard[0]
    rule = next(iter(compatible_rules(e)))
    raw = f"HYP {e.operator} {rule} {e.eid}"
    assert parse_hypotheses(raw, shard, w.operators) == [(e.operator, rule, e.eid)]
    assert parse_rules(f"RULE {e.operator} {rule}", w.operators) == {e.operator: rule}

    f = field_new(w)
    events = admit_hypotheses(w, f, shard, 0, 0, [(e.operator, rule, e.eid)])
    assert events[0]["decision"] == "SUPPORT"
    rev = f["revision"]
    admit_hypotheses(w, f, shard, 0, 1, [])
    assert f["revision"] == rev
    bad_rule = next(r for r in RULES if apply_rule(e.inp, r) != e.out)
    events = admit_hypotheses(w, f, shard, 0, 2, [(e.operator, bad_rule, e.eid)])
    assert events[0]["decision"] == "REJECT"

    return {
        "status": "PASS",
        "world_invariant_local_ambiguous": "PASS",
        "world_invariant_joint_unique": "PASS",
        "parser": "PASS",
        "admission": "PASS",
        "revision_semantics": "PASS",
        "provenance": "PASS",
    }


def model_preflight(runner: Runner, model_id: str) -> dict:
    if runner.mock:
        return {"status": "PASS", "mode": "MOCK"}

    op = "KEM"
    e = Evidence("PF-KEM-P0", op, "ABCDE", apply_rule("ABCDE", "REVERSE"), 0)
    prompt = f"""Infer the latent rule for the operator from one unambiguous training example.
RULE CATALOG:
{RULE_CATALOG}
Return a line containing operator, rule name, and evidence id.
FORMAT: HYP <operator> <rule_name> <evidence_id>
YOUR EVIDENCE:
{evidence_text([e])}
GOVERNED RELATIONAL FIELD:
- KEM: PENDING NONE
"""
    raw = runner.run(prompt, model_id, 48)
    parsed = parse_hypotheses(raw, [e], [op])
    if not parsed or parsed[0][1] != "REVERSE":
        raise RuntimeError(f"MODEL_PREFLIGHT_FAILED hypothesis interface: {raw[:300]!r}")

    d_prompt = direct_prompt(evidence_text([e]), [op])
    d_raw = runner.run(d_prompt, model_id, 48)
    pred = parse_rules(d_raw, [op])
    if pred.get(op) != "REVERSE":
        raise RuntimeError(f"MODEL_PREFLIGHT_FAILED direct interface: {d_raw[:300]!r}")

    return {
        "status": "PASS",
        "hypothesis_raw": raw[:300],
        "direct_raw": d_raw[:300],
    }


def run_direct(runner: Runner, model_id: str, context: str, operators: List[str], prior=None) -> tuple[Dict[str, str], str]:
    raw = runner.run(direct_prompt(context, operators, prior), model_id)
    return parse_rules(raw, operators), raw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260819)
    ap.add_argument("--worlds", type=int, default=3)
    ap.add_argument("--participants", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--operators", type=int, default=3)
    ap.add_argument("--model-a", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--self-test-only", action="store_true")
    ap.add_argument("--no-4bit", action="store_true")
    ap.add_argument("--out", default="/content/tofoo_relational_results_v2")
    ap.add_argument("--min-direct-coverage", type=float, default=0.60)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "test": "TOFOO_RELATIONAL_EMERGENCE_V2",
        "seed": args.seed,
        "worlds": args.worlds,
        "participants": args.participants,
        "rounds": args.rounds,
        "operators": args.operators,
        "model_a": args.model_a,
        "mock_mode": args.mock,
        "primary_metric": "relational_rule_accuracy - max(isolated_max, pooled_raw, structured_raw, pooled_iterative)",
        "phenomenon_invariant": "NO_SINGLE_SHARD_UNIQUELY_IDENTIFIES_RULE; JOINT_CROSS_PARTICIPANT_EVIDENCE_DOES",
        "controls": [
            "ISOLATED",
            "POOLED_RAW",
            "STRUCTURED_RAW",
            "POOLED_ITERATIVE_MATCHED_CALLS",
            "ORACLE_DSL_INTERSECTION",
            "RELATIONAL_ADAPTIVE",
        ],
        "invariants": [
            "NO_DIRECT_RELATIONAL_STATE_WRITE_PATH",
            "NO_HIDDEN_HOLDOUT_ADMISSION",
            "LOCAL_PROVENANCE_REQUIRED_FOR_SUPPORT",
            "MODEL_CANNOT_SELF_AUTHORIZE_ADMISSION",
            "ALL_PARTICIPANTS_REQUIRED_FOR_RULE_ADMISSION",
            "HOLDOUT_NEVER_USED_FOR_ADMISSION",
        ],
    }

    try:
        manifest["self_check"] = selfcheck()
    except Exception as exc:
        manifest.update(instrument_status="TEST_INVALID_SELF_CHECK", error=str(exc))
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(json.dumps(manifest, indent=2))
        return 2

    if args.self_test_only:
        manifest["instrument_status"] = "SELF_CHECK_PASS"
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(json.dumps(manifest, indent=2))
        return 0

    runner = Runner(mock=args.mock, use_4bit=not args.no_4bit)
    try:
        manifest["model_preflight"] = model_preflight(runner, args.model_a)
    except Exception as exc:
        manifest.update(instrument_status="TEST_INVALID_MODEL_PREFLIGHT", error=str(exc))
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(json.dumps(manifest, indent=2))
        return 3

    summaries = []
    raw_calls = []
    admission_events = []
    fields = {}
    total_direct_expected = 0
    total_direct_parsed = 0

    for wi in range(args.worlds):
        world = make_world(args.seed + wi, f"W{wi}", args.participants, args.operators)

        isolated = []
        isolated_transfer = []
        for p, shard in enumerate(world.shards):
            pred, raw = run_direct(runner, args.model_a, evidence_text(shard), world.operators)
            total_direct_expected += len(world.operators)
            total_direct_parsed += len(pred)
            acc = mapping_accuracy(pred, world.truth)
            tx = transfer_accuracy(pred, world.transfer)
            isolated.append(acc)
            isolated_transfer.append(tx)
            raw_calls.append({"world": world.wid, "condition": "ISOLATED", "participant": p,
                              "pred": pred, "raw": raw[:1200], "rule_accuracy": acc, "transfer": tx})

        pooled_pred, pooled_raw = run_direct(runner, args.model_a, pooled_text(world), world.operators)
        total_direct_expected += len(world.operators)
        total_direct_parsed += len(pooled_pred)
        pooled_acc = mapping_accuracy(pooled_pred, world.truth)
        pooled_tx = transfer_accuracy(pooled_pred, world.transfer)
        raw_calls.append({"world": world.wid, "condition": "POOLED_RAW", "pred": pooled_pred,
                          "raw": pooled_raw[:1200], "rule_accuracy": pooled_acc, "transfer": pooled_tx})

        structured_pred, structured_raw = run_direct(runner, args.model_a, structured_text(world), world.operators)
        total_direct_expected += len(world.operators)
        total_direct_parsed += len(structured_pred)
        structured_acc = mapping_accuracy(structured_pred, world.truth)
        structured_tx = transfer_accuracy(structured_pred, world.transfer)
        raw_calls.append({"world": world.wid, "condition": "STRUCTURED_RAW", "pred": structured_pred,
                          "raw": structured_raw[:1200], "rule_accuracy": structured_acc, "transfer": structured_tx})

        pooled_iter_pred = {}
        pooled_iter_raw = []
        for step in range(args.rounds * args.participants):
            pred, raw = run_direct(runner, args.model_a, structured_text(world), world.operators, pooled_iter_pred)
            if pred:
                pooled_iter_pred.update(pred)
            pooled_iter_raw.append(raw[:800])
            total_direct_expected += len(world.operators)
            total_direct_parsed += len(pred)
        pooled_iter_acc = mapping_accuracy(pooled_iter_pred, world.truth)
        pooled_iter_tx = transfer_accuracy(pooled_iter_pred, world.transfer)
        raw_calls.append({"world": world.wid, "condition": "POOLED_ITERATIVE_MATCHED_CALLS",
                          "pred": pooled_iter_pred, "raw": pooled_iter_raw,
                          "rule_accuracy": pooled_iter_acc, "transfer": pooled_iter_tx})

        oracle_pred = oracle_mapping(world)
        oracle_acc = mapping_accuracy(oracle_pred, world.truth)
        oracle_tx = transfer_accuracy(oracle_pred, world.transfer)

        field = field_new(world)
        relational_recognized = 0
        for rnd in range(args.rounds):
            for p, shard in enumerate(world.shards):
                prompt = participant_prompt(world, shard, field, rnd)
                raw = runner.run(prompt, args.model_a)
                parsed = parse_hypotheses(raw, shard, world.operators)
                relational_recognized += len(parsed)
                raw_calls.append({"world": world.wid, "condition": "RELATIONAL_ADAPTIVE",
                                  "round": rnd, "participant": p, "parsed": parsed, "raw": raw[:1200]})
                events = admit_hypotheses(world, field, shard, p, rnd, parsed)
                admission_events.extend({"world": world.wid, **e} for e in events)

        relational_pred = dict(field["admitted"])
        relational_acc = mapping_accuracy(relational_pred, world.truth)
        relational_tx = transfer_accuracy(relational_pred, world.transfer)
        fields[world.wid] = field

        comparator = max(max(isolated), pooled_acc, structured_acc, pooled_iter_acc)
        comparator_tx = max(max(isolated_transfer), pooled_tx, structured_tx, pooled_iter_tx)
        summaries.append({
            "world": world.wid,
            "truth": world.truth,
            "isolated_max": max(isolated),
            "pooled_raw": pooled_acc,
            "structured_raw": structured_acc,
            "pooled_iterative": pooled_iter_acc,
            "oracle_dsl": oracle_acc,
            "relational": relational_acc,
            "relational_surplus": relational_acc - comparator,
            "isolated_transfer_max": max(isolated_transfer),
            "pooled_raw_transfer": pooled_tx,
            "structured_raw_transfer": structured_tx,
            "pooled_iterative_transfer": pooled_iter_tx,
            "oracle_transfer": oracle_tx,
            "relational_transfer": relational_tx,
            "relational_transfer_surplus": relational_tx - comparator_tx,
            "field_revision": field["revision"],
            "field_admitted": relational_pred,
            "recognized_hypotheses": relational_recognized,
        })

    keys = [
        "isolated_max", "pooled_raw", "structured_raw", "pooled_iterative", "oracle_dsl",
        "relational", "relational_surplus", "isolated_transfer_max", "pooled_raw_transfer",
        "structured_raw_transfer", "pooled_iterative_transfer", "oracle_transfer",
        "relational_transfer", "relational_transfer_surplus",
    ]
    diagnostics = {k: sum(x[k] for x in summaries) / len(summaries) for k in keys}
    diagnostics["direct_parse_coverage"] = (
        total_direct_parsed / total_direct_expected if total_direct_expected else 0.0
    )
    diagnostics["recognized_hypotheses"] = sum(x["recognized_hypotheses"] for x in summaries)
    diagnostics["model_calls"] = runner.calls
    diagnostics["approx_input_tokens"] = runner.input_tokens
    diagnostics["output_chars"] = runner.output_chars

    if diagnostics["oracle_dsl"] != 1.0 or diagnostics["oracle_transfer"] != 1.0:
        status = "TEST_INVALID_WORLD_OR_ORACLE"
    elif diagnostics["direct_parse_coverage"] < args.min_direct_coverage:
        status = "TEST_INVALID_DIRECT_INTERFACE"
    elif diagnostics["recognized_hypotheses"] == 0:
        status = "TEST_INVALID_NO_RELATIONAL_HYPOTHESES"
    else:
        status = "VALID_SIGNAL_DISCOVERY_RUN"

    if status != "VALID_SIGNAL_DISCOVERY_RUN":
        interpretation = "DO_NOT_INTERPRET_AS_RESEARCH_RESULT"
    elif diagnostics["relational_surplus"] > 0 and diagnostics["relational_transfer_surplus"] > 0:
        interpretation = "POSITIVE_RELATIONAL_SURPLUS_CANDIDATE_UNNORMALIZED"
    else:
        interpretation = "NO_RELATIONAL_SURPLUS_IN_THIS_RUN"

    manifest.update(
        instrument_status=status,
        interpretation=interpretation,
        diagnostics=diagnostics,
        budget_note=(
            "POOLED_ITERATIVE uses the same model-call count as RELATIONAL_ADAPTIVE per world, "
            "but token budgets may still differ; report them before any research claim."
        ),
    )

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (out / "summary.json").write_text(json.dumps(summaries, indent=2))
    (out / "raw_calls.json").write_text(json.dumps(raw_calls, indent=2))
    (out / "fields.json").write_text(json.dumps({
        wid: {
            "admitted": f["admitted"],
            "unresolved": f["unresolved"],
            "revision": f["revision"],
            "attempts": f["attempts"],
            "mutations": f["mutations"],
            "supports": f["supports"],
        }
        for wid, f in fields.items()
    }, indent=2))
    with (out / "admission_events.jsonl").open("w") as fh:
        for event in admission_events:
            fh.write(json.dumps(event) + "\n")

    print(json.dumps({"status": status, "interpretation": interpretation, "diagnostics": diagnostics}, indent=2))
    print(json.dumps(summaries, indent=2))
    if status != "VALID_SIGNAL_DISCOVERY_RUN":
        print("TEST INVALID: do not interpret scores.", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
