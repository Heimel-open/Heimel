"""ExternalAdapter base + generic FunctionAdapter and RESTAdapter."""

import importlib
from abc import abstractmethod
from typing import Any, Callable, Dict, Optional

import requests

from vaig.instruments.base import InstrumentBase


class ExternalAdapter(InstrumentBase):
    """
    Generell base for eksterne governance-verktøy.

    Subklassen setter:
      name    — slot-navn, brukes av Dirigenten (f.eks. "presidio_pii")
      _import — Python-pakke som må være installert (f.eks. "presidio_analyzer")
      _call   — selve kallet som returnerer 0.0–1.0
    """

    name: str = ""
    _import: str = ""
    priority: int = 10
    timeout_seconds: float = 5.0

    @classmethod
    def is_available(cls) -> bool:
        if not cls._import:
            return True
        try:
            importlib.import_module(cls._import)
            return True
        except ImportError:
            return False

    def score(self, prompt: str, response: str, generate_fn=None) -> float:
        try:
            result = self._call(prompt, response)
            return max(0.0, min(1.0, float(result)))
        except Exception:
            return 0.0

    @abstractmethod
    def _call(self, prompt: str, response: str) -> float:
        """Kall det eksterne verktøyet. Returner 0.0–1.0."""
        ...


def _resolve_dotted(obj: Any, path: str) -> float:
    """Walk a dotted key path into a nested dict/object and return the leaf as float."""
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj[part]
        else:
            obj = getattr(obj, part)
    return float(obj)


class FunctionAdapter(ExternalAdapter):
    """Wraps any callable (prompt, response) -> float as an ExternalAdapter."""

    _import: str = ""

    def __init__(
        self,
        name: str,
        fn: Callable[[str, str], float],
        import_check: Optional[str] = None,
    ) -> None:
        self.name = name
        self._fn = fn
        # Defer availability check to an instance attribute so is_available()
        # still works correctly when called on the class vs. instance.
        self._import_check = import_check or ""

    @classmethod
    def is_available(cls) -> bool:
        return True

    def _call(self, prompt: str, response: str) -> float:
        if self._import_check:
            importlib.import_module(self._import_check)
        return self._fn(prompt, response)


class RESTAdapter(ExternalAdapter):
    """Calls any HTTP endpoint and extracts a float score via a dotted field path."""

    _import: str = ""

    def __init__(
        self,
        name: str,
        url: str,
        score_field: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        payload_template: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self._url = url
        self._score_field = score_field
        self._method = method.upper()
        self._headers = headers or {}
        self._payload_template = payload_template

    def _call(self, prompt: str, response: str) -> float:
        if self._payload_template is not None:
            payload = {
                k: v.format(prompt=prompt, response=response) if isinstance(v, str) else v
                for k, v in self._payload_template.items()
            }
        else:
            payload = {"prompt": prompt, "response": response}

        try:
            resp = requests.request(
                self._method,
                self._url,
                json=payload,
                headers=self._headers,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            return _resolve_dotted(resp.json(), self._score_field)
        except Exception:
            return 0.0
