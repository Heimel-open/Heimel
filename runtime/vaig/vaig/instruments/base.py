"""Base class for all VAIG instruments (blind men)."""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Tuple


class InstrumentBase(ABC):
    """
    One bounded evaluation instrument.

    Instruments declare runtime dependencies explicitly. Missing native inputs
    and missing calibration are represented by the Ensemble as typed states;
    they must never be converted to a measured 0.0 risk score.
    """

    name: str = ""
    requires_generate_fn: bool = False
    required_native_inputs: Tuple[str, ...] = ()
    requires_calibration: bool = False
    # P0.5 (full): instruments that must be judged by a *separate* model
    # (not the same generate_fn that produced the response) declare this. When
    # no judge_fn is supplied at evaluation time, the ensemble fails the slot
    # closed (UNCALIBRATED) instead of silently self-judging.
    requires_judge_fn: bool = False
    priority: int = 1
    version: str = "unversioned"
    # P0.5: instruments that evaluate the same model that produced the output
    # (LLM-as-self-judge) must declare this so the report can flag the limited
    # independence of that measurement. A genuinely independent judge sets this
    # False (the default) and is invoked via a separate judge_fn, not the same
    # generate_fn that produced the response.
    self_judging: bool = False

    @classmethod
    def is_available(cls) -> bool:
        """Return whether implementation dependencies are installed."""
        return True

    def is_calibrated(self) -> bool:
        """Return whether a required calibration artifact is bound."""
        return not self.requires_calibration

    def calibration_profile_id(self) -> Optional[str]:
        """Return the exact calibration profile/version used by this instance."""
        return None

    @abstractmethod
    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
    ) -> float:
        """Return a measured risk score in [0, 1].

        ``judge_fn`` (if supplied) is a *separate* model used to judge this
        instrument's output. For self-judging instruments it may be None and
        ``generate_fn`` is used instead; the ensemble flags such slots as
        ``self_judging`` and, when ``requires_judge_fn`` is set, fails them
        closed if no judge is available.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(slot={self.name!r}, priority={self.priority})"
