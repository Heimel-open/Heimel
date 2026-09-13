from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import shutil
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
except ImportError:
    def retry(*args, **kwargs):
        def decorator(f):
            return f
        return decorator
    stop_after_attempt = wait_exponential = retry_if_exception_type = lambda *args, **kwargs: None

RUN_ROOT = Path(os.getenv("P12_RUN_ROOT", "/tmp/p12_synapse"))
RUN_ROOT.mkdir(parents=True, exist_ok=True)

def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name) or default

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ModelSpec:
    name: str
    provider: str
    model: str
    api_key_name: str

MODEL_POOL = [
    ModelSpec(
        name="openai",
        provider="openai",
        model=get_secret("P12_OPENAI_MODEL", "gpt-5.2"),
        api_key_name="OPENAI_API_KEY",
    ),
    ModelSpec(
        name="anthropic",
        provider="anthropic",
        model=get_secret("P12_ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        api_key_name="ANTHROPIC_API_KEY",
    ),
    ModelSpec(
        name="gemini",
        provider="gemini",
        model=get_secret("P12_GEMINI_MODEL", "gemini-3.6-flash"),
        api_key_name="GEMINI_API_KEY",
    ),
]

JUDGE_NAMES = [
    x.strip() for x in os.getenv("P12_JUDGES", "openai,anthropic").split(",") if x.strip()
]
TOTAL_OUTPUT_BUDGET = int(os.getenv("P12_TOTAL_OUTPUT_BUDGET", "1600"))
GLOBAL_SEED = int(os.getenv("P12_GLOBAL_SEED", "12082026"))
MOCK_MODE = os.getenv("P12_MOCK_MODE", "false").lower() in {"1", "true", "yes"}
CONDITIONS = ["C0", "C1", "C3", "C5"]

def validate_config() -> None:
    if len(MODEL_POOL) != 3:
        raise ValueError("P12 MVP krever nøyaktig tre modeller.")
    unknown_judges = sorted(set(JUDGE_NAMES) - {m.name for m in MODEL_POOL})
    if unknown_judges:
        raise ValueError(f"Ukjente dommere: {unknown_judges}")
    missing = [m.api_key_name for m in MODEL_POOL if not get_secret(m.api_key_name)]
    if missing and not MOCK_MODE:
        raise RuntimeError("Mangler API-nøkler: " + ", ".join(sorted(set(missing))))

def load_tasks(path: str | Path) -> list[dict[str, Any]]:
    tasks = json.loads(Path(path).read_text(encoding="utf-8"))
    if len(tasks) != 40:
        raise ValueError(f"Forventet 40 oppgaver, fikk {len(tasks)}")
    return tasks


DIMENSIONS = {
    "S": "semantic_preservation",
    "I": "evidence_integration",
    "R": "belief_revision",
    "T": "transfer",
    "C": "causal_reasoning",
    "P": "premise_reconstruction",
    "E": "error_detection",
    "K": "calibration",
}

def task_prompt(task: dict[str, Any], stage: int = 1, previous_answer: Optional[str] = None) -> str:
    lines = [f"OPPGAVE {task['id']} — {task['title']}"]
    lines.append("")
    lines.append("KILDEPAKKE:")
    for item in task["packet"]:
        lines.append(f"{item['label']}: {item['text']}")
    lines.append("")
    lines.append("SPØRSMÅL:")
    lines.append(task["question"])

    if stage == 1 and task.get("late_evidence"):
        lines.append("")
        lines.append("Dette er fase 1. Gi en foreløpig vurdering. Marker premisser og usikkerhet.")
    elif stage == 2:
        lines.append("")
        lines.append("TIDLIGERE SVAR:")
        lines.append(previous_answer or "")
        lines.append("")
        lines.append("SEN EVIDENS:")
        for idx, evidence in enumerate(task.get("late_evidence", []), start=1):
            lines.append(f"S{idx}: {evidence}")
        lines.append("")
        lines.append(
            "Revider konklusjonen. Vis eksplisitt hva som endret seg, hvilke premisser som falt, "
            "og hva som fortsatt er usikkert. Ikke lat som den nye evidensen var kjent tidligere."
        )

    lines.append("")
    lines.append(
        "Svar faglig og kort. Skill fakta, tolkning, hypotese og konklusjon. "
        "Ikke bruk kunnskap utenfor kildepakken som om den var dokumentert her."
    )
    return "\n".join(lines)

def stable_seed(*parts: Any) -> int:
    raw = "|".join(str(p) for p in parts).encode()
    return int(hashlib.sha256(raw).hexdigest()[:16], 16)


@dataclass
class CallResult:
    call_id: str
    provider: str
    model: str
    text: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]
    max_output_tokens: int
    started_at: str
    elapsed_seconds: float
    raw_usage: dict[str, Any]
    error: Optional[str] = None

class ProviderError(RuntimeError):
    pass

def _safe_dump(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    for method in ("model_dump", "to_dict", "dict"):
        fn = getattr(obj, method, None)
        if callable(fn):
            try:
                value = fn()
                if isinstance(value, dict):
                    return value
            except Exception:
                pass
    return {"repr": repr(obj)}

def _usage_values(usage: Any) -> tuple[Optional[int], Optional[int], Optional[int], dict[str, Any]]:
    d = _safe_dump(usage)

    def find(keys: list[str]) -> Optional[int]:
        for key in keys:
            value = d.get(key)
            if isinstance(value, int):
                return value
        for value in d.values():
            if isinstance(value, dict):
                for key in keys:
                    nested = value.get(key)
                    if isinstance(nested, int):
                        return nested
        return None

    inp = find(["input_tokens", "prompt_tokens", "prompt_token_count", "input_token_count"])
    out = find(["output_tokens", "completion_tokens", "candidates_token_count", "output_token_count"])
    total = find(["total_tokens", "total_token_count"])
    if total is None and inp is not None and out is not None:
        total = inp + out
    return inp, out, total, d

_clients: dict[str, Any] = {}

def get_client(spec: ModelSpec) -> Any:
    cache_key = f"{spec.provider}:{spec.name}"
    if cache_key in _clients:
        return _clients[cache_key]

    api_key = get_secret(spec.api_key_name)
    if not api_key and not MOCK_MODE:
        raise RuntimeError(f"Mangler nøkkel: {spec.api_key_name}")

    if spec.provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    elif spec.provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
    elif spec.provider == "gemini":
        from google import genai
        client = genai.Client(api_key=api_key)
    else:
        raise ValueError(f"Ukjent provider: {spec.provider}")

    _clients[cache_key] = client
    return client

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ProviderError, TimeoutError, ConnectionError)),
    reraise=True,
)
def call_model(
    spec: ModelSpec,
    system: str,
    prompt: str,
    max_output_tokens: int,
) -> CallResult:
    started = time.perf_counter()
    started_at = utc_now()
    call_id = str(uuid.uuid4())

    if MOCK_MODE:
        text = (
            f"[MOCK {spec.name}] Premisser kartlagt. Konflikt kontrollert. "
            f"Konklusjon avgrenset. Prompt-hash={hashlib.sha256(prompt.encode()).hexdigest()[:8]}"
        )
        elapsed = time.perf_counter() - started
        return CallResult(
            call_id, spec.provider, spec.model, text,
            max(1, len(prompt) // 4), min(80, max_output_tokens), None,
            max_output_tokens, started_at, elapsed, {"mock": True}
        )

    try:
        client = get_client(spec)

        if spec.provider == "openai":
            response = client.responses.create(
                model=spec.model,
                instructions=system,
                input=prompt,
                max_output_tokens=max_output_tokens,
            )
            text = getattr(response, "output_text", "") or ""
            usage = getattr(response, "usage", None)

        elif spec.provider == "anthropic":
            response = client.messages.create(
                model=spec.model,
                max_tokens=max_output_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                getattr(block, "text", "")
                for block in getattr(response, "content", [])
                if getattr(block, "type", None) == "text"
            )
            usage = getattr(response, "usage", None)

        elif spec.provider == "gemini":
            from google.genai import types
            response = client.models.generate_content(
                model=spec.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_output_tokens,
                ),
            )
            text = getattr(response, "text", "") or ""
            usage = getattr(response, "usage_metadata", None)

        else:
            raise ValueError(spec.provider)

        if not text.strip():
            raise ProviderError(f"Tomt svar fra {spec.provider}/{spec.model}")

        inp, out, total, raw = _usage_values(usage)
        return CallResult(
            call_id=call_id,
            provider=spec.provider,
            model=spec.model,
            text=text.strip(),
            input_tokens=inp,
            output_tokens=out,
            total_tokens=total,
            max_output_tokens=max_output_tokens,
            started_at=started_at,
            elapsed_seconds=time.perf_counter() - started,
            raw_usage=raw,
        )

    except Exception as exc:
        name = type(exc).__name__
        retryable_names = {
            "RateLimitError", "APITimeoutError", "APIConnectionError",
            "InternalServerError", "ServiceUnavailableError",
        }
        if name in retryable_names or "429" in str(exc) or "timeout" in str(exc).lower():
            raise ProviderError(str(exc)) from exc
        raise

def model_by_name(name: str) -> ModelSpec:
    matches = [m for m in MODEL_POOL if m.name == name]
    if not matches:
        raise KeyError(name)
    return matches[0]


BASE_SYSTEM = (
    "Du deltar i en kontrollert forskningsprotokoll. Bruk bare oppgitt kildepakke. "
    "Skill observasjon, tolkning, hypotese og konklusjon. Bevar uløst konflikt. "
    "Oppgi usikkerhet når evidensen ikke bærer en sikker konklusjon."
)

ROLE_SYSTEMS = {
    "hypothesis": (
        BASE_SYSTEM + " Din rolle er hypotese- og premisskartlegger. "
        "Lag eksplisitte kandidathypoteser, nødvendige premisser og hva som ville falsifisert dem."
    ),
    "evidence": (
        BASE_SYSTEM + " Din rolle er evidensrevisor. "
        "Knytt alle påstander til kildeetiketter, finn manglende data og ranger evidensstyrke."
    ),
    "counter": (
        BASE_SYSTEM + " Din rolle er motargument- og konfliktrevisor. "
        "Søk sterkeste alternative forklaring, skjulte motsetninger og falsk konsensus."
    ),
}

SYNTHESIS_SYSTEM = (
    BASE_SYSTEM + " Du er synteseansvarlig. "
    "Integrer bidragene i et claim/evidence-register. Ikke avgjør ved flertall. "
    "Bevar minoritetsinnvendinger, revider premisser og avslutt med kalibrert konklusjon."
)

ISOLATED_SYSTEM = (
    BASE_SYSTEM + " Løs oppgaven selvstendig. Du ser ikke andre modellers arbeid."
)

AGGREGATOR_SYSTEM = (
    BASE_SYSTEM + " Du er en fast aggregator for isolerte svar. "
    "Du skal ikke anta at flertallet har rett. Sammenstill og velg den konklusjonen "
    "som best støttes av kildepakken. Marker uløst uenighet."
)

RANDOM_SYNTH_SYSTEM = (
    BASE_SYSTEM + " Kombiner fragmentene til ett svar. Fragmentenes rekkefølge og roller "
    "er tilfeldig og skal ikke tolkes som en epistemisk struktur."
)

@dataclass
class ConditionResult:
    condition: str
    task_id: str
    stage: int
    answer: str
    trace: list[dict[str, Any]]
    max_output_budget: int
    observed_output_tokens: Optional[int]
    model_route: dict[str, str]
    randomization: Optional[dict[str, Any]]

def _sum_output_tokens(trace: list[CallResult]) -> Optional[int]:
    values = [c.output_tokens for c in trace if c.output_tokens is not None]
    return sum(values) if values else None

def _trace_dicts(trace: list[CallResult]) -> list[dict[str, Any]]:
    return [asdict(c) for c in trace]

def _rotated_specs(task_id: str, stage: int) -> list[ModelSpec]:
    shift = stable_seed(GLOBAL_SEED, task_id, stage, "route") % len(MODEL_POOL)
    return MODEL_POOL[shift:] + MODEL_POOL[:shift]

def run_condition_once(
    condition: str,
    task: dict[str, Any],
    stage: int,
    prompt: str,
    budget: int,
) -> ConditionResult:
    specs = _rotated_specs(task["id"], stage)
    trace: list[CallResult] = []
    route: dict[str, str] = {}
    randomization = None

    if condition == "C0":
        spec = specs[0]
        route["solver"] = f"{spec.provider}:{spec.model}"
        call = call_model(spec, ISOLATED_SYSTEM, prompt, budget)
        trace.append(call)
        answer = call.text

    elif condition == "C1":
        indiv_budget = max(100, round(budget * 0.21875))
        agg_budget = budget - 3 * indiv_budget
        candidates = []
        for idx, spec in enumerate(specs, start=1):
            route[f"candidate_{idx}"] = f"{spec.provider}:{spec.model}"
            call = call_model(spec, ISOLATED_SYSTEM, prompt, indiv_budget)
            trace.append(call)
            candidates.append(f"KANDIDAT {idx}:\n{call.text}")
        aggregator = specs[0]
        route["aggregator"] = f"{aggregator.provider}:{aggregator.model}"
        agg_prompt = (
            prompt + "\n\nISOLERTE KANDIDATSVAR:\n\n" + "\n\n".join(candidates)
            + "\n\nLag endelig svar. Ikke innfør nye eksterne fakta."
        )
        call = call_model(aggregator, AGGREGATOR_SYSTEM, agg_prompt, agg_budget)
        trace.append(call)
        answer = call.text

    elif condition in {"C3", "C5"}:
        node_budget = max(100, round(budget * 0.1875))
        synth_budget = budget - 3 * node_budget

        if condition == "C3":
            roles = ["hypothesis", "evidence", "counter"]
            node_outputs = []
            for role, spec in zip(roles, specs):
                route[role] = f"{spec.provider}:{spec.model}"
                call = call_model(spec, ROLE_SYSTEMS[role], prompt, node_budget)
                trace.append(call)
                node_outputs.append(f"{role.upper()}-NODE:\n{call.text}")
            synthesis_prompt = (
                prompt
                + "\n\nSTRUKTURERTE NODEBIDRAG:\n\n"
                + "\n\n".join(node_outputs)
                + "\n\nBygg eksplisitt premisskart, konfliktregister og kalibrert konklusjon."
            )
            synthesizer = specs[0]
            route["synthesizer"] = f"{synthesizer.provider}:{synthesizer.model}"
            call = call_model(synthesizer, SYNTHESIS_SYSTEM, synthesis_prompt, synth_budget)
            trace.append(call)
            answer = call.text

        else:
            rng = random.Random(stable_seed(GLOBAL_SEED, task["id"], stage, "C5"))
            base_roles = ["hypothesis", "evidence", "counter"]
            assigned_roles = [rng.choice(base_roles) for _ in range(3)]
            node_outputs = []
            for idx, (role, spec) in enumerate(zip(assigned_roles, specs), start=1):
                route[f"random_node_{idx}"] = f"{spec.provider}:{spec.model}"
                call = call_model(spec, ROLE_SYSTEMS[role], prompt, node_budget)
                trace.append(call)
                node_outputs.append(call.text)

            order = list(range(3))
            rng.shuffle(order)
            shuffled = [node_outputs[i] for i in order]
            random_labels = ["FRAGMENT-Q", "FRAGMENT-M", "FRAGMENT-Z"]
            rng.shuffle(random_labels)
            randomization = {
                "assigned_roles": assigned_roles,
                "fragment_order": order,
                "fragment_labels": random_labels,
            }
            fragments = [
                f"{label}:\n{text}" for label, text in zip(random_labels, shuffled)
            ]
            synthesizer = specs[0]
            route["synthesizer"] = f"{synthesizer.provider}:{synthesizer.model}"
            synthesis_prompt = (
                prompt
                + "\n\nUSTRUKTURERTE FRAGMENTER:\n\n"
                + "\n\n".join(fragments)
                + "\n\nLag ett endelig svar."
            )
            call = call_model(synthesizer, RANDOM_SYNTH_SYSTEM, synthesis_prompt, synth_budget)
            trace.append(call)
            answer = call.text

    else:
        raise ValueError(condition)

    return ConditionResult(
        condition=condition,
        task_id=task["id"],
        stage=stage,
        answer=answer,
        trace=_trace_dicts(trace),
        max_output_budget=budget,
        observed_output_tokens=_sum_output_tokens(trace),
        model_route=route,
        randomization=randomization,
    )

def run_task_condition(condition: str, task: dict[str, Any]) -> dict[str, Any]:
    if task.get("late_evidence"):
        stage_budget = TOTAL_OUTPUT_BUDGET // 2
        p1 = task_prompt(task, stage=1)
        r1 = run_condition_once(condition, task, 1, p1, stage_budget)
        p2 = task_prompt(task, stage=2, previous_answer=r1.answer)
        r2 = run_condition_once(condition, task, 2, p2, TOTAL_OUTPUT_BUDGET - stage_budget)
        answer = (
            "FASE 1 — FORELØPIG SVAR\n"
            + r1.answer
            + "\n\nFASE 2 — REVIDERT SVAR\n"
            + r2.answer
        )
        trace = r1.trace + r2.trace
        observed = None
        vals = [v for v in [r1.observed_output_tokens, r2.observed_output_tokens] if v is not None]
        if vals:
            observed = sum(vals)
        return {
            "condition": condition,
            "task_id": task["id"],
            "answer": answer,
            "stages": [asdict(r1), asdict(r2)],
            "trace": trace,
            "max_output_budget": TOTAL_OUTPUT_BUDGET,
            "observed_output_tokens": observed,
        }

    prompt = task_prompt(task, stage=1)
    result = run_condition_once(condition, task, 1, prompt, TOTAL_OUTPUT_BUDGET)
    return {
        "condition": condition,
        "task_id": task["id"],
        "answer": result.answer,
        "stages": [asdict(result)],
        "trace": result.trace,
        "max_output_budget": TOTAL_OUTPUT_BUDGET,
        "observed_output_tokens": result.observed_output_tokens,
    }


JUDGE_SYSTEM = (
    "Du er en blind evaluator i en forhåndsregistrert studie. "
    "Du får ikke vite hvilken eksperimentbetingelse som produserte svaret. "
    "Vurder substans, ikke stil, lengde eller leverandør. "
    "Bruk bare kildepakken, forventede elementer og failure modes. "
    "Returner kun gyldig JSON."
)

def judge_prompt(task: dict[str, Any], answer: str) -> str:
    active = [DIMENSIONS[d] for d in task["active_dimensions"]]
    schema_scores = ",\n".join(
        f'    "{name}": null' for name in DIMENSIONS.values()
    )
    packet = "\n".join(f"{x['label']}: {x['text']}" for x in task["packet"])
    late = "\n".join(task.get("late_evidence", [])) or "(ingen)"
    return f'''TASK: {task["id"]} — {task["title"]}

KILDEPAKKE:
{packet}

SPØRSMÅL:
{task["question"]}

SEN EVIDENS:
{late}

FORVENTEDE ELEMENTER:
{json.dumps(task["expected_elements"], ensure_ascii=False)}

KRITISKE FEILMODI:
{json.dumps(task["failure_modes"], ensure_ascii=False)}

AKTIVE DIMENSJONER:
{json.dumps(active, ensure_ascii=False)}

KANDIDATSVAR:
{answer}

Poengsett bare aktive dimensjoner fra 0 til 4:
0 = kritisk feil eller helt manglende
1 = svak, vesentlig feil
2 = delvis riktig, viktige mangler
3 = riktig med mindre mangler
4 = presis, komplett og kalibrert

Inaktive dimensjoner skal være null.

Returner nøyaktig dette JSON-formatet:
{{
  "scores": {{
{schema_scores}
  }},
  "fatal_error": false,
  "fatal_error_reason": "",
  "supported_elements": [],
  "missing_elements": [],
  "brief_rationale": ""
}}'''.strip()

def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))

def validate_judgment(task: dict[str, Any], obj: dict[str, Any]) -> dict[str, Any]:
    scores = obj.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("Judge mangler scores.")
    active_names = {DIMENSIONS[d] for d in task["active_dimensions"]}
    clean_scores: dict[str, Optional[float]] = {}
    for name in DIMENSIONS.values():
        value = scores.get(name)
        if name in active_names:
            if not isinstance(value, (int, float)) or not 0 <= float(value) <= 4:
                raise ValueError(f"Ugyldig aktiv score {name}: {value}")
            clean_scores[name] = float(value)
        else:
            clean_scores[name] = None
    obj["scores"] = clean_scores
    obj["fatal_error"] = bool(obj.get("fatal_error", False))
    return obj

def blind_id(task_id: str, condition: str) -> str:
    return hashlib.sha256(
        f"{GLOBAL_SEED}|{task_id}|{condition}".encode()
    ).hexdigest()[:12]

def judge_answer(
    task: dict[str, Any],
    condition: str,
    answer: str,
    judge_name: str,
) -> dict[str, Any]:
    spec = model_by_name(judge_name)
    if MOCK_MODE:
        active_names = {DIMENSIONS[d] for d in task["active_dimensions"]}
        scores = {name: (3.0 if name in active_names else None) for name in DIMENSIONS.values()}
        return {
            "blind_id": blind_id(task["id"], condition),
            "judge": judge_name,
            "judge_provider": spec.provider,
            "judge_model": spec.model,
            "judgment": {
                "scores": scores,
                "fatal_error": False,
                "fatal_error_reason": "",
                "supported_elements": task["expected_elements"][:2],
                "missing_elements": [],
                "brief_rationale": "MOCK",
            },
            "call": {
                "call_id": str(uuid.uuid4()),
                "provider": spec.provider,
                "model": spec.model,
                "text": "{\"mock\": true}",
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": 2,
                "max_output_tokens": 650,
                "started_at": utc_now(),
                "elapsed_seconds": 0.0,
                "raw_usage": {"mock": True},
                "error": None,
            },
        }
    result = call_model(
        spec,
        JUDGE_SYSTEM,
        judge_prompt(task, answer),
        max_output_tokens=650,
    )
    parsed = validate_judgment(task, parse_json_object(result.text))
    return {
        "blind_id": blind_id(task["id"], condition),
        "judge": judge_name,
        "judge_provider": spec.provider,
        "judge_model": spec.model,
        "judgment": parsed,
        "call": asdict(result),
    }


CANONICAL_TASK_PACK_SHA256 = "e5eec7868ba9e8737c3f6a9200036819b97b9659df0a4e7c628c8d95ccffc05a"
TASK_PACK_SHA256 = CANONICAL_TASK_PACK_SHA256

def new_run_dir(label: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RUN_ROOT / f"{stamp}_{label}"
    path.mkdir(parents=True, exist_ok=False)
    return path

def task_pack_sha256(tasks: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(tasks, ensure_ascii=False, indent=2).encode()
    ).hexdigest()

def preregistration(run_dir: Path, task_ids: list[str], conditions: list[str], task_sha: str) -> dict[str, Any]:
    record = {
        "protocol": "P12-Synapse-MVP-v1",
        "created_at": utc_now(),
        "global_seed": GLOBAL_SEED,
        "task_pack_sha256": task_sha,
        "task_ids": task_ids,
        "conditions": conditions,
        "total_output_budget_per_task_condition": TOTAL_OUTPUT_BUDGET,
        "models": [asdict(m) for m in MODEL_POOL],
        "judges": JUDGE_NAMES,
        "primary_hypotheses": {
            "H1": "U(C3) > max(U(C0), U(C1))",
            "H2": "U(C3) > U(C5)",
            "decision_rule": (
                "C3 viser positiv gevinst i minst tre av fire familier "
                "og slår C5 på T1 og T2."
            ),
        },
        "dimensions": DIMENSIONS,
        "mock_mode": MOCK_MODE,
    }
    (run_dir / "preregistration.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return record

def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out

def run_experiment(
    tasks: list[dict[str, Any]],
    task_limit: Optional[int] = None,
    conditions: Optional[list[str]] = None,
    label: str = "run",
    existing_run_dir: Optional[str] = None,
) -> Path:
    validate_config()
    selected_tasks = tasks[:task_limit] if task_limit else tasks
    selected_conditions = conditions or CONDITIONS

    run_dir = Path(existing_run_dir) if existing_run_dir else new_run_dir(label)
    run_dir.mkdir(parents=True, exist_ok=True)

    raw_path = run_dir / "raw_outputs.jsonl"
    judge_path = run_dir / "judgments.jsonl"

    done_outputs = {
        (r["task_id"], r["condition"]) for r in load_jsonl(raw_path)
    }
    done_judges = {
        (r["task_id"], r["condition"], r["judge"]) for r in load_jsonl(judge_path)
    }

    if not (run_dir / "preregistration.json").exists():
        actual_sha = task_pack_sha256(tasks)
        if actual_sha != CANONICAL_TASK_PACK_SHA256:
            raise ValueError(
                f"Task pack SHA mismatch: {actual_sha} != {CANONICAL_TASK_PACK_SHA256}"
            )
        preregistration(
            run_dir,
            [t["id"] for t in selected_tasks],
            selected_conditions,
            actual_sha,
        )

    for task_idx, task in enumerate(selected_tasks, start=1):
        for condition in selected_conditions:
            key = (task["id"], condition)
            if key not in done_outputs:
                print(f"[{task_idx}/{len(selected_tasks)}] {task['id']} {condition}")
                output = run_task_condition(condition, task)
                output["family"] = task["family"]
                output["title"] = task["title"]
                output["created_at"] = utc_now()
                append_jsonl(raw_path, output)
            else:
                output = next(
                    r for r in load_jsonl(raw_path)
                    if r["task_id"] == task["id"] and r["condition"] == condition
                )

            for judge_name in JUDGE_NAMES:
                jkey = (task["id"], condition, judge_name)
                if jkey in done_judges:
                    continue
                print(f"  judge={judge_name}")
                selected = judge_answer(task, condition, output["answer"], judge_name)
                selected["task_id"] = task["id"]
                selected["family"] = task["family"]
                selected["condition"] = condition
                selected["created_at"] = utc_now()
                append_jsonl(judge_path, selected)
                done_judges.add(jkey)

    print("Ferdig:", run_dir)
    return run_dir


def judgments_frame(run_dir: Path) -> pd.DataFrame:
    rows = []
    for item in load_jsonl(run_dir / "judgments.jsonl"):
        judgment = item["judgment"]
        for dim, score in judgment["scores"].items():
            if score is None:
                continue
            rows.append({
                "task_id": item["task_id"],
                "family": item["family"],
                "condition": item["condition"],
                "judge": item["judge"],
                "dimension": dim,
                "score": float(score),
                "fatal_error": bool(judgment.get("fatal_error", False)),
            })
    return pd.DataFrame(rows)

def aggregate_scores(run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    long = judgments_frame(run_dir)
    if long.empty:
        raise ValueError("Ingen judgment-data.")

    per_task = (
        long.groupby(["task_id", "family", "condition"], as_index=False)
        .agg(score=("score", "mean"), fatal_rate=("fatal_error", "mean"))
    )
    summary = (
        per_task.groupby(["family", "condition"], as_index=False)
        .agg(mean_score=("score", "mean"), n=("task_id", "nunique"))
    )
    return per_task, summary

def bootstrap_paired_diff(
    per_task: pd.DataFrame,
    a: str,
    b: str,
    n_boot: int = 5000,
    seed: int = GLOBAL_SEED,
) -> dict[str, float]:
    pivot = per_task.pivot_table(index="task_id", columns="condition", values="score")
    paired = pivot[[a, b]].dropna()
    if paired.empty:
        return {"mean": math.nan, "low": math.nan, "high": math.nan, "n": 0}
    diffs = (paired[a] - paired[b]).to_numpy()
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        sample = [diffs[rng.randrange(len(diffs))] for _ in range(len(diffs))]
        means.append(sum(sample) / len(sample))
    means.sort()
    low = means[int(0.025 * len(means))]
    high = means[int(0.975 * len(means))]
    return {
        "mean": float(sum(diffs) / len(diffs)),
        "low": float(low),
        "high": float(high),
        "n": int(len(diffs)),
    }

def decision_report(run_dir: Path) -> dict[str, Any]:
    per_task, summary = aggregate_scores(run_dir)
    pivot_family = summary.pivot(index="family", columns="condition", values="mean_score")

    family_gains = {}
    for family, row in pivot_family.iterrows():
        baselines = [row.get("C0"), row.get("C1")]
        baselines = [x for x in baselines if pd.notna(x)]
        best_base = max(baselines) if baselines else math.nan
        family_gains[family] = {
            "C3_minus_best_base": float(row.get("C3") - best_base)
                if pd.notna(row.get("C3")) and not math.isnan(best_base) else math.nan,
            "C3_minus_C5": float(row.get("C3") - row.get("C5"))
                if pd.notna(row.get("C3")) and pd.notna(row.get("C5")) else math.nan,
        }

    positive_families = sum(
        1 for value in family_gains.values()
        if value["C3_minus_best_base"] > 0
    )
    t1_t2_c5 = all(
        family_gains.get(f, {}).get("C3_minus_C5", math.nan) > 0
        for f in ["T1", "T2"]
        if f in family_gains
    )

    report = {
        "created_at": utc_now(),
        "family_gains": family_gains,
        "positive_families": positive_families,
        "c3_beats_c5_on_t1_t2": t1_t2_c5,
        "mvp_decision_rule_pass": positive_families >= 3 and t1_t2_c5,
        "paired_bootstrap": {
            "C3-C0": bootstrap_paired_diff(per_task, "C3", "C0"),
            "C3-C1": bootstrap_paired_diff(per_task, "C3", "C1"),
            "C3-C5": bootstrap_paired_diff(per_task, "C3", "C5"),
        },
    }
    (run_dir / "decision_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    per_task.to_csv(run_dir / "scores_per_task.csv", index=False)
    summary.to_csv(run_dir / "score_summary.csv", index=False)
    return report

def plot_summary(run_dir: Path) -> None:
    _, summary = aggregate_scores(run_dir)
    for family in sorted(summary["family"].unique()):
        subset = summary[summary["family"] == family].sort_values("condition")
        plt.figure(figsize=(7, 4))
        plt.bar(subset["condition"], subset["mean_score"])
        plt.ylim(0, 4)
        plt.title(f"{family}: gjennomsnittlig blind score")
        plt.xlabel("Betingelse")
        plt.ylabel("Score 0–4")
        plt.show()


def budget_frame(run_dir: Path) -> pd.DataFrame:
    rows = []
    for item in load_jsonl(run_dir / "raw_outputs.jsonl"):
        rows.append({
            "task_id": item["task_id"],
            "family": item["family"],
            "condition": item["condition"],
            "max_output_budget": item["max_output_budget"],
            "observed_output_tokens": item.get("observed_output_tokens"),
        })
    return pd.DataFrame(rows)

def judge_agreement(run_dir: Path) -> pd.DataFrame:
    long = judgments_frame(run_dir)
    per_judge_task = (
        long.groupby(["task_id", "condition", "judge"], as_index=False)
        .agg(score=("score", "mean"))
    )
    pivot = per_judge_task.pivot_table(
        index=["task_id", "condition"], columns="judge", values="score"
    )
    if len(JUDGE_NAMES) >= 2 and all(j in pivot.columns for j in JUDGE_NAMES[:2]):
        a, b = JUDGE_NAMES[:2]
        return pd.DataFrame({
            "metric": ["pearson", "mean_absolute_difference", "n"],
            "value": [
                pivot[a].corr(pivot[b]),
                (pivot[a] - pivot[b]).abs().mean(),
                pivot[[a, b]].dropna().shape[0],
            ],
        })
    return pd.DataFrame({"metric": ["n"], "value": [len(pivot)]})


def zip_run(run_dir: Path) -> Path:
    return Path(shutil.make_archive(str(run_dir), "zip", root_dir=run_dir))
