"""Judge factory — build a ``judge_fn`` from a ``JudgeSpec``.

The orchestrator's ``judge_fn`` slot is a plain callable, so the factory can
produce any judge (hosted, local, deterministic) without changing the
ensemble. The spec is carried alongside so every decision is attributable.
"""

from __future__ import annotations

from typing import Callable

from vaig.judge.providers import JudgeProvider
from vaig.judge.spec import JudgeSpec


class JudgeFactory:
    """Build judge callables from specs through one provider."""

    def __init__(self, provider: JudgeProvider) -> None:
        self.provider = provider

    def build(self, spec: JudgeSpec) -> Callable[[str], str]:
        """Return a judge function pinned to ``spec``."""

        def judge(prompt: str) -> str:
            return self.provider.complete(prompt, spec)

        return judge
