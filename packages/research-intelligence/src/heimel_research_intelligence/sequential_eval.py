from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Callable, Iterable, Sequence


class SequentialEvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class Exposure:
    index: int
    content: str
    content_sha256: str

    @classmethod
    def create(cls, index: int, content: str) -> "Exposure":
        if index < 0:
            raise SequentialEvaluationError("exposure index must be non-negative")
        digest = "sha256:" + sha256(content.encode("utf-8")).hexdigest()
        return cls(index=index, content=content, content_sha256=digest)


@dataclass(frozen=True)
class Observation:
    exposure_index: int
    exposure_sha256: str
    response: str
    response_sha256: str
    memory_before_sha256: str
    memory_after_sha256: str


@dataclass(frozen=True)
class SequentialEvaluationResult:
    observations: tuple[Observation, ...]
    memory: tuple[str, ...]
    stopped_at: int | None
    recall: str | None
    trace_sha256: str


Observer = Callable[[Exposure, tuple[str, ...]], str]
StopRule = Callable[[Exposure, str, tuple[str, ...]], bool]
RecallProbe = Callable[[tuple[str, ...]], str]
MemoryReducer = Callable[[tuple[str, ...], Exposure, str], Sequence[str]]


def _hash_text(text: str) -> str:
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


def _hash_memory(memory: Sequence[str]) -> str:
    return _hash_text("\x1f".join(memory))


def bounded_append(max_items: int) -> MemoryReducer:
    if max_items < 0:
        raise SequentialEvaluationError("max_items must be non-negative")

    def reduce(memory: tuple[str, ...], exposure: Exposure, response: str) -> Sequence[str]:
        if max_items == 0:
            return ()
        return (*memory, response)[-max_items:]

    return reduce


def run_sequential_evaluation(
    passages: Iterable[str],
    *,
    observer: Observer,
    memory_reducer: MemoryReducer,
    stop_rule: StopRule | None = None,
    recall_probe: RecallProbe | None = None,
) -> SequentialEvaluationResult:
    """Evaluate irreversible sequential exposure without re-reading source passages.

    The observer receives only the current exposure plus bounded derived memory.
    The recall probe receives only the final derived memory. Source passages are
    intentionally not available to recall, preventing source re-read leakage.
    """

    memory: tuple[str, ...] = ()
    observations: list[Observation] = []
    stopped_at: int | None = None

    for index, content in enumerate(passages):
        exposure = Exposure.create(index, content)
        before_hash = _hash_memory(memory)
        response = observer(exposure, memory)
        if not isinstance(response, str):
            raise SequentialEvaluationError("observer must return str")

        next_memory = tuple(memory_reducer(memory, exposure, response))
        after_hash = _hash_memory(next_memory)
        observations.append(
            Observation(
                exposure_index=index,
                exposure_sha256=exposure.content_sha256,
                response=response,
                response_sha256=_hash_text(response),
                memory_before_sha256=before_hash,
                memory_after_sha256=after_hash,
            )
        )
        memory = next_memory

        if stop_rule is not None and stop_rule(exposure, response, memory):
            stopped_at = index
            break

    recall = recall_probe(memory) if recall_probe is not None else None
    trace_material = "\n".join(
        f"{o.exposure_index}|{o.exposure_sha256}|{o.response_sha256}|{o.memory_before_sha256}|{o.memory_after_sha256}"
        for o in observations
    )
    trace_sha256 = _hash_text(trace_material)
    return SequentialEvaluationResult(
        observations=tuple(observations),
        memory=memory,
        stopped_at=stopped_at,
        recall=recall,
        trace_sha256=trace_sha256,
    )


def compare_reruns(results: Sequence[SequentialEvaluationResult]) -> dict[str, object]:
    if not results:
        raise SequentialEvaluationError("at least one result is required")
    trace_hashes = tuple(result.trace_sha256 for result in results)
    recall_hashes = tuple(_hash_text(result.recall or "") for result in results)
    return {
        "runs": len(results),
        "trace_hashes": trace_hashes,
        "recall_hashes": recall_hashes,
        "trace_stable": len(set(trace_hashes)) == 1,
        "recall_stable": len(set(recall_hashes)) == 1,
    }
