"""Judge factory & multiverse — model-, sampling- and provider-aware judging."""

from vaig.judge.evaluator import JudgeEvaluation, JudgeModelEvaluator, LabeledCase
from vaig.judge.factory import JudgeFactory
from vaig.judge.multiverse import (
    JudgeMultiverse,
    MultiverseReport,
    MultiverseRun,
    RunCase,
    default_run_case,
)
from vaig.judge.providers import (
    DEFAULT_CHAT_URL,
    DeterministicJudgeProvider,
    HTTPJudgeProvider,
    JudgeProvider,
    VerdictMapProvider,
)
from vaig.judge.spec import JudgeSpec

__all__ = [
    "JudgeSpec",
    "JudgeFactory",
    "JudgeProvider",
    "HTTPJudgeProvider",
    "DeterministicJudgeProvider",
    "VerdictMapProvider",
    "DEFAULT_CHAT_URL",
    "JudgeMultiverse",
    "MultiverseReport",
    "MultiverseRun",
    "RunCase",
    "default_run_case",
    "JudgeModelEvaluator",
    "JudgeEvaluation",
    "LabeledCase",
]
