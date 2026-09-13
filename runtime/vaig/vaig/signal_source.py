"""
Signal source contract for P0.3 (bind a real model signal into the integrity
layer).

The integrity instruments (e.g. ``logprob_scorer``) consume *native* model
signals -- per-token log probabilities, or activation / attention probe
vectors -- drawn from the model actually under governance. Those signals must
come from a concrete, identifiable source, never from a placeholder, and the
layer must fail closed when the source is unavailable or returns malformed
data.

This module defines the ``SignalSource`` contract plus a static fake
(``StaticSignalSource``) used by tests and local runs. The production source
that talks to a real model API (logprob endpoint, probe endpoint) is
implemented by the team per their API surface; it only has to satisfy
``SignalSource.fetch`` and expose a stable ``id``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vaig.model_signals import ModelSignalBundle


class SignalUnavailableError(Exception):
    """Raised when a signal source cannot produce a valid signal bundle.

    Treated as a fail-closed condition by the ensemble: the dependent
    instrument is marked UNAVAILABLE / not admissible rather than scored as a
    silent 0.0.
    """


@runtime_checkable
class SignalSource(Protocol):
    """A provider of native model signals for one governed response.

    Implementations must expose a stable ``id`` (for audit traceability) and a
    ``fetch`` method that returns a validated :class:`ModelSignalBundle`.
    ``fetch`` should raise on any failure (network, API, malformed payload);
    the ensemble converts that into a fail-closed instrument result.
    """

    id: str

    def fetch(self, prompt: str, response: str) -> ModelSignalBundle:
        """Return native signals for ``response`` to the governed ``prompt``.

        Raises :class:`SignalUnavailableError` (or any exception) when no valid
        signal can be produced.
        """
        ...


class StaticSignalSource:
    """A fixed, in-memory signal source (tests and local dry runs).

    Wraps a pre-built :class:`ModelSignalBundle` and returns it on every
    ``fetch``. Set ``fail_with`` to simulate an unavailable source so the
    fail-closed path can be exercised without a real model API.
    """

    def __init__(
        self,
        bundle: ModelSignalBundle,
        id: str = "static-signal-source",
        fail_with: Exception | None = None,
    ) -> None:
        self._bundle = bundle
        self.id = id
        self.fail_with = fail_with

    def fetch(self, prompt: str, response: str) -> ModelSignalBundle:
        if self.fail_with is not None:
            raise self.fail_with
        return self._bundle
