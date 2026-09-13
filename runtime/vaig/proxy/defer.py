"""DEFER queue — holds flagged responses pending human review."""
import json
import threading
import time
import uuid


class DeferQueue:
    def __init__(self):
        self._lock = threading.Lock()
        self._queue: dict[str, dict] = {}

    def add(self, path: str, input_body: bytes, response_body: bytes,
            scout_result: dict, gate_result: dict) -> str:
        review_id = str(uuid.uuid4())[:8]
        with self._lock:
            self._queue[review_id] = {
                "id": review_id,
                "ts": time.time(),
                "path": path,
                "input_preview": _safe_preview(input_body),
                "output_preview": _safe_preview(response_body),
                "scout": scout_result,
                "gate": gate_result,
                "decision": None,
                "response_body": response_body,
                "content_type": "application/json",
            }
        return review_id

    def get(self, review_id: str) -> dict | None:
        with self._lock:
            return self._queue.get(review_id)

    def decide(self, review_id: str, decision: str) -> bool:
        with self._lock:
            if review_id not in self._queue:
                return False
            self._queue[review_id]["decision"] = decision
            return True

    def all_pending(self) -> list[dict]:
        with self._lock:
            return [
                {k: v for k, v in item.items() if k != "response_body"}
                for item in self._queue.values()
                if item["decision"] is None
            ]

    def all_recent(self, limit: int = 50) -> list[dict]:
        with self._lock:
            items = sorted(self._queue.values(), key=lambda x: x["ts"], reverse=True)
            return [
                {k: v for k, v in item.items() if k != "response_body"}
                for item in items[:limit]
            ]


def _safe_preview(body: bytes, max_chars: int = 500) -> str:
    if not body:
        return ""
    try:
        data = json.loads(body)
        if "messages" in data:
            msgs = data["messages"]
            if msgs:
                last = msgs[-1]
                content = last.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        p.get("text", "") for p in content if isinstance(p, dict)
                    )
                return str(content)[:max_chars]
        if "content" in data:
            return str(data["content"])[:max_chars]
        if "choices" in data:
            choices = data["choices"]
            if choices:
                msg = choices[0].get("message", {})
                return str(msg.get("content", ""))[:max_chars]
        return json.dumps(data)[:max_chars]
    except (json.JSONDecodeError, KeyError, TypeError):
        try:
            return body.decode()[:max_chars]
        except Exception:
            return "[binary]"
