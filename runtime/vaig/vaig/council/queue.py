"""CouncilQueue — thread-safe queue for L3/L4 decisions awaiting human review."""

import threading
import time
import uuid
from typing import Dict, List, Optional

from vaig.council.schema import CouncilItem


class CouncilQueue:
    """
    L6 — Thread-safe queue for L3/L4 decisions awaiting human review.

    Usage:
        q = CouncilQueue()
        item_id = q.submit(orchestrator_result, prompt, response)
        q.verdict(item_id, "APPROVE")
    """

    def __init__(self):
        self._items: Dict[str, CouncilItem] = {}
        self._lock = threading.Lock()

    def submit(self, result, prompt: str = "", response: str = "") -> str:
        """Submit an OrchestratorResult for human review. Returns item id."""
        level = result.level.value if hasattr(result.level, "value") else str(result.level)
        terrain = getattr(result, "terrain", None)
        domain = terrain.domain.value if terrain else "UNKNOWN"
        validation = getattr(result, "validation", None)
        scores = validation.scores if validation else {}
        return self._enqueue(level, domain, prompt, response, scores)

    def submit_raw(
        self,
        level: str,
        domain: str,
        prompt: str,
        response: str,
        scores: Optional[Dict[str, float]] = None,
    ) -> str:
        """Submit raw fields (for HTTP endpoint or proxy use)."""
        return self._enqueue(level, domain, prompt, response, scores or {})

    def _enqueue(
        self, level: str, domain: str, prompt: str, response: str, scores: Dict[str, float]
    ) -> str:
        item_id = str(uuid.uuid4())[:8]
        item = CouncilItem(
            id=item_id,
            ts=time.time(),
            level=level,
            domain=domain,
            prompt_preview=prompt[:500],
            response_preview=response[:500],
            scores=scores,
        )
        with self._lock:
            self._items[item_id] = item
        return item_id

    def verdict(self, item_id: str, decision: str) -> bool:
        """
        Record a human verdict. decision: "APPROVE" | "REJECT" | "OVERRIDE"
        Returns True if item found and updated.
        """
        if decision not in ("APPROVE", "REJECT", "OVERRIDE"):
            raise ValueError(f"Invalid verdict: {decision!r}. Must be APPROVE, REJECT, or OVERRIDE.")
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return False
            item.verdict = decision
            item.verdict_ts = time.time()
            return True

    def get(self, item_id: str) -> Optional[CouncilItem]:
        with self._lock:
            return self._items.get(item_id)

    def pending(self) -> List[CouncilItem]:
        with self._lock:
            return [i for i in self._items.values() if i.is_pending]

    def recent(self, limit: int = 50) -> List[CouncilItem]:
        with self._lock:
            items = sorted(self._items.values(), key=lambda i: i.ts, reverse=True)
            return items[:limit]

    def stats(self) -> dict:
        with self._lock:
            all_items = list(self._items.values())
        total = len(all_items)
        pending = sum(1 for i in all_items if i.is_pending)
        approved = sum(1 for i in all_items if i.verdict == "APPROVE")
        rejected = sum(1 for i in all_items if i.verdict == "REJECT")
        overridden = sum(1 for i in all_items if i.verdict == "OVERRIDE")
        by_domain: Dict[str, int] = {}
        for i in all_items:
            by_domain[i.domain] = by_domain.get(i.domain, 0) + 1
        by_level: Dict[str, int] = {}
        for i in all_items:
            by_level[i.level] = by_level.get(i.level, 0) + 1
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "overridden": overridden,
            "by_domain": by_domain,
            "by_level": by_level,
        }
