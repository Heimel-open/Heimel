from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations, product

RULES: dict[str, tuple[int, ...]] = {
    "IDENTITY": (0, 1, 2, 3, 4),
    "REVERSE": (4, 3, 2, 1, 0),
    "ROTL1": (1, 2, 3, 4, 0),
    "ROTR1": (4, 0, 1, 2, 3),
    "SWAP12": (1, 0, 2, 3, 4),
    "SWAP45": (0, 1, 2, 4, 3),
    "PAIRSWAP": (1, 0, 3, 2, 4),
    "EVENS_FIRST": (0, 2, 4, 1, 3),
}
RULE_NAMES: tuple[str, ...] = tuple(RULES)
LETTERS: tuple[str, ...] = tuple(chr(ord("A") + i) for i in range(len(RULE_NAMES)))
RULE_TO_LETTER: dict[str, str] = dict(zip(RULE_NAMES, LETTERS, strict=True))
LETTER_TO_RULE: dict[str, str] = dict(zip(LETTERS, RULE_NAMES, strict=True))


@dataclass(frozen=True)
class Evidence:
    eid: str
    operator: str
    inp: str
    out: str
    participant: int


@dataclass(frozen=True)
class World:
    wid: str
    truth: dict[str, str]
    shards: tuple[tuple[Evidence, ...], ...]

    @property
    def operators(self) -> tuple[str, ...]:
        return tuple(self.truth)

    def evidence_for(self, operator: str) -> tuple[Evidence, ...]:
        return tuple(
            evidence
            for shard in self.shards
            for evidence in shard
            if evidence.operator == operator
        )


def apply_rule(seq: str, rule_name: str) -> str:
    if len(seq) != 5:
        raise ValueError("latent-rule inputs must contain exactly five characters")
    return "".join(seq[index] for index in RULES[rule_name])


def compatible_rules(evidence: Evidence) -> frozenset[str]:
    return frozenset(
        rule for rule in RULE_NAMES if apply_rule(evidence.inp, rule) == evidence.out
    )


@lru_cache(maxsize=1)
def training_bank() -> tuple[str, ...]:
    return tuple(
        "".join(chars)
        for chars in product("ABC", repeat=5)
        if 2 <= len(set(chars)) <= 3
    )


def find_ambiguous_examples(rule_name: str, count: int, seed: int) -> tuple[tuple[str, str], ...]:
    rng = random.Random(seed)
    candidates: list[tuple[str, str, frozenset[str]]] = []
    for inp in training_bank():
        out = apply_rule(inp, rule_name)
        evidence = Evidence("candidate", "OP", inp, out, 0)
        compatible = compatible_rules(evidence)
        if rule_name in compatible and len(compatible) >= 2:
            candidates.append((inp, out, compatible))
    rng.shuffle(candidates)

    for pool in (candidates[:120], candidates):
        for combo in combinations(pool, count):
            joint = set(RULE_NAMES)
            for _, _, compatible in combo:
                joint.intersection_update(compatible)
            if joint == {rule_name}:
                return tuple((inp, out) for inp, out, _ in combo)
    raise RuntimeError(f"unable to construct ambiguous evidence for {rule_name}")


def make_world(
    seed: int,
    wid: str,
    *,
    participants: int = 3,
    operator_count: int = 3,
) -> World:
    if participants < 2:
        raise ValueError("participants must be >= 2")
    if operator_count < 2 or operator_count > 4:
        raise ValueError("operator_count must be between 2 and 4")

    operator_names = ("KEM", "RIV", "TOV", "SUL")[:operator_count]
    rng = random.Random(seed)
    chosen_rules = rng.sample(list(RULE_NAMES), operator_count)
    truth = dict(zip(operator_names, chosen_rules, strict=True))
    shards: list[list[Evidence]] = [[] for _ in range(participants)]

    for operator_index, operator in enumerate(operator_names):
        examples = find_ambiguous_examples(
            truth[operator], participants, seed + 1009 * (operator_index + 1)
        )
        for participant, (inp, out) in enumerate(examples):
            shards[participant].append(
                Evidence(
                    eid=f"{wid}-{operator}-P{participant}",
                    operator=operator,
                    inp=inp,
                    out=out,
                    participant=participant,
                )
            )

    world = World(wid=wid, truth=truth, shards=tuple(tuple(shard) for shard in shards))
    validate_world(world)
    return world


def validate_world(world: World) -> None:
    for operator, truth in world.truth.items():
        evidence = world.evidence_for(operator)
        if len(evidence) != len(world.shards):
            raise AssertionError(f"{world.wid}/{operator}: one evidence item per participant required")
        local_sets = [compatible_rules(item) for item in evidence]
        if any(len(local) < 2 for local in local_sets):
            raise AssertionError(f"{world.wid}/{operator}: local evidence must remain ambiguous")
        joint = set(RULE_NAMES)
        for local in local_sets:
            joint.intersection_update(local)
        if joint != {truth}:
            raise AssertionError(
                f"{world.wid}/{operator}: joint evidence must uniquely identify {truth}; got {joint}"
            )


def format_evidence(items: Iterable[Evidence]) -> str:
    return "\n".join(
        f"[{item.eid}] input={item.inp} output={item.out} participant={item.participant}"
        for item in items
    )


def choice_lines() -> str:
    return "\n".join(
        f"{letter}) {rule}: output positions "
        + " ".join(str(index + 1) for index in RULES[rule])
        for letter, rule in zip(LETTERS, RULE_NAMES, strict=True)
    )


def extract_answer_letter(text: str) -> str | None:
    """Extract only an explicit `ANSWER: <letter>` submission.

    Malformed model submissions are model outcomes, not harness errors.
    """
    matches: list[str] = []
    for line in text.splitlines():
        stripped = line.strip().upper()
        if not stripped.startswith("ANSWER:"):
            continue
        answer = stripped.removeprefix("ANSWER:").strip()
        if answer in LETTER_TO_RULE:
            matches.append(answer)
    if len(matches) != 1:
        return None
    return matches[0]


@dataclass
class GovernedField:
    participants: int
    supports: dict[str, set[int]] = field(
        default_factory=lambda: {rule: set() for rule in RULE_NAMES}
    )
    admitted_rule: str | None = None
    unresolved: tuple[str, ...] = ()
    revision: int = 0

    def propose(self, participant: int, rule: str, evidence: Evidence) -> bool:
        """Validate local provenance/semantics, then record support.

        Returns True only when authoritative field state mutated.
        """
        if participant != evidence.participant:
            return False
        if rule not in compatible_rules(evidence):
            return False

        supporters = self.supports[rule]
        if participant in supporters:
            return False
        supporters.add(participant)
        self.revision += 1
        self._recompute()
        return True

    def _recompute(self) -> None:
        fully_supported = tuple(
            rule for rule in RULE_NAMES if len(self.supports[rule]) == self.participants
        )
        if len(fully_supported) == 1:
            self.admitted_rule = fully_supported[0]
            self.unresolved = ()
        elif len(fully_supported) > 1:
            self.admitted_rule = None
            self.unresolved = fully_supported

    def render(self) -> str:
        if self.admitted_rule:
            return f"ADMITTED: {RULE_TO_LETTER[self.admitted_rule]} ({self.admitted_rule})"
        lines = ["PENDING SUPPORT:"]
        for rule in RULE_NAMES:
            supporters = sorted(self.supports[rule])
            if supporters:
                lines.append(
                    f"- {RULE_TO_LETTER[rule]} ({rule}): participants={supporters}"
                )
        if len(lines) == 1:
            lines.append("- none")
        return "\n".join(lines)
