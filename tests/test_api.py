"""End-to-end tests for the local LastSeen HTTP API and web UI."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from valo_edge.lastseen import LastSeenService
from valo_edge.lastseen.api import LastSeenHTTPServer


def _request(method: str, url: str, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


@pytest.fixture()
def api(tmp_path):
    service = LastSeenService(tmp_path / "api.db")
    httpd = LastSeenHTTPServer(("127.0.0.1", 0), service)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        service.close()
        thread.join(timeout=5)


def test_web_ui_is_served(api):
    with urllib.request.urlopen(f"{api}/", timeout=5) as response:
        assert response.status == 200
        assert response.headers["Content-Type"].startswith("text/html")
        assert "LastSeen" in response.read().decode("utf-8")


def test_remember_find_delete_receipt_round_trip(api):
    status, stored = _request(
        "POST",
        f"{api}/observations",
        {
            "object_name": "keys",
            "location": "kitchen counter",
            "camera_id": "kitchen-01",
            "zone_id": "counter",
            "confidence": 0.98,
            "aliases": ["nøkler"],
        },
    )
    assert status == 201
    assert stored["object"] == "keys"
    assert len(stored["source_receipt"]) == 64

    status, found = _request("GET", f"{api}/objects/keys/last-seen")
    assert status == 200
    assert found["location"] == "kitchen counter"
    assert found["source_id"] == stored["source_id"]

    status, found = _request("GET", f"{api}/objects/n%C3%B8kler/last-seen")
    assert status == 200
    assert found["source_id"] == stored["source_id"]

    status, deleted = _request("DELETE", f"{api}/objects/keys")
    assert status == 200
    assert deleted["deleted_observations"] == 1
    assert len(deleted["receipt_digest"]) == 64

    status, missing = _request("GET", f"{api}/objects/keys/last-seen")
    assert status == 404

    status, receipt = _request("GET", f"{api}/receipts/{deleted['receipt_digest']}")
    assert status == 200
    assert receipt["kind"] == "deletion"


def test_observation_source_receipt_lookup(api):
    status, stored = _request(
        "POST",
        f"{api}/observations",
        {"object_name": "wallet", "location": "hallway shelf"},
    )
    assert status == 201
    status, receipt = _request("GET", f"{api}/receipts/{stored['source_receipt']}")
    assert status == 200
    assert receipt["kind"] == "observation"
    assert receipt["source_id"] == stored["source_id"]


def test_unknown_receipt_returns_404(api):
    status, _ = _request("GET", f"{api}/receipts/{'f' * 64}")
    assert status == 404


def test_query_scope_is_enforced_before_results(api):
    _request(
        "POST",
        f"{api}/observations",
        {"object_name": "glasses", "location": "office desk", "camera_id": "office-01"},
    )
    status, found = _request("GET", f"{api}/objects/glasses/last-seen?camera_id=living-room-01")
    assert status == 404
    status, found = _request("GET", f"{api}/objects/glasses/last-seen?camera_id=office-01")
    assert status == 200
    assert found["location"] == "office desk"


def test_missing_field_returns_400(api):
    status, error = _request("POST", f"{api}/observations", {"object_name": "keys"})
    assert status == 400
    assert "missing required field" in error["error"]
