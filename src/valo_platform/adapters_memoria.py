from __future__ import annotations

from typing import Any, Sequence

import httpx

from src.valo_platform.memory_provider import MemoryMutationEvent, MemoryRecord


class MemoriaUnavailable(RuntimeError):
    pass


class MemoriaAdapter:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 5.0,
        read_only_on_failure: bool = True,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._read_only_on_failure = read_only_on_failure
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.AsyncClient(headers=headers, timeout=timeout_seconds)
        self._degraded = False

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._degraded and method.upper() != "GET":
            raise MemoriaUnavailable("Memoria is degraded; writes fail closed")
        try:
            response = await self._client.request(method, f"{self._base_url}{path}", **kwargs)
            response.raise_for_status()
            self._degraded = False
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            self._degraded = self._read_only_on_failure
            raise MemoriaUnavailable("Memoria request failed") from exc

    async def create_snapshot(self, branch: str) -> str:
        data = await self._request("POST", "/snapshots", json={"branch": branch})
        return str(data["snapshot_id"])

    async def create_branch(self, branch: str, from_snapshot: str | None = None) -> str:
        data = await self._request(
            "POST", "/branches", json={"branch": branch, "from_snapshot": from_snapshot}
        )
        return str(data["branch"])

    async def store_memory(self, *, content: Any, metadata: dict[str, Any]) -> MemoryRecord:
        data = await self._request("POST", "/memories", json={"content": content, "metadata": metadata})
        return MemoryRecord.model_validate(data)

    async def retrieve_memory(self, memory_id: str) -> MemoryRecord | None:
        try:
            data = await self._request("GET", f"/memories/{memory_id}")
        except MemoriaUnavailable:
            return None
        return MemoryRecord.model_validate(data)

    async def search_memory(self, query: str, *, branch: str, limit: int = 20) -> Sequence[MemoryRecord]:
        try:
            data = await self._request(
                "GET", "/memories/search", params={"query": query, "branch": branch, "limit": limit}
            )
        except MemoriaUnavailable:
            return ()
        return tuple(MemoryRecord.model_validate(item) for item in data.get("items", []))

    async def diff_branch(self, branch: str, against: str) -> dict[str, Any]:
        return await self._request("GET", f"/branches/{branch}/diff", params={"against": against})

    async def merge_branch(self, branch: str, target: str) -> str:
        data = await self._request("POST", f"/branches/{branch}/merge", json={"target": target})
        return str(data["snapshot_id"])

    async def rollback_branch(self, branch: str, snapshot_id: str) -> str:
        data = await self._request(
            "POST", f"/branches/{branch}/rollback", json={"snapshot_id": snapshot_id}
        )
        return str(data["snapshot_id"])

    async def quarantine_memory(self, memory_id: str, reason: str) -> MemoryRecord:
        data = await self._request(
            "POST", f"/memories/{memory_id}/quarantine", json={"reason": reason}
        )
        return MemoryRecord.model_validate(data)

    async def purge_memory(self, memory_id: str, reason: str) -> MemoryMutationEvent:
        data = await self._request("DELETE", f"/memories/{memory_id}", json={"reason": reason})
        return MemoryMutationEvent.model_validate(data)

    async def health(self) -> dict[str, Any]:
        try:
            data = await self._request("GET", "/health")
            return {"status": "ok", "degraded": False, "provider": "memoria", **data}
        except MemoriaUnavailable:
            return {"status": "unavailable", "degraded": self._degraded, "provider": "memoria"}

    async def close(self) -> None:
        await self._client.aclose()
