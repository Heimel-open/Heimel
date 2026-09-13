"""Tests for isolated Wigolo / WorldMonitor adapters (issue #812).

Source-integrity contract (mirrors #878):
- no fabricated values;
- raw payload + canonical digest preserved;
- malformed / empty / error responses fail closed.
"""

import json
from unittest import mock

import pytest

from src.valo_platform.speider_connectors import WigoloConnector, WorldMonitorConnector


def _payload(items):
    return {"observations": items}


def test_wigolo_returns_provenance_tagged_candidates():
    conn = WigoloConnector(base_url="https://api.wigolo.test", api_key="k")
    fake = _payload([
        {"id": "w1", "title": "Brand mention", "score": 0.9},
        {"id": "w2", "title": "Sentiment drop", "score": 0.4},
    ])
    with mock.patch("valo_platform.speider_connectors.external_monitor_connectors.httpx.get") as g:
        g.return_value = mock.Mock(status_code=200, json=lambda: fake, raise_for_status=lambda: None)
        out = conn.fetch_observations("acme")

    assert len(out) == 2
    for c in out:
        assert c["source"] == "Wigolo"
        assert c["query"] == "acme"
        assert c["raw_digest"]
        assert c["provenance"]["source"] == "Wigolo"
        assert c["provenance"]["raw_digest"] == c["raw_digest"]
        # payload preserved unmapped
        assert "id" in c["payload"]


def test_digest_changes_when_payload_changes():
    conn = WigoloConnector(base_url="https://api.wigolo.test")
    a = _payload([{"id": "x", "v": 1}])
    b = _payload([{"id": "x", "v": 2}])
    with mock.patch("valo_platform.speider_connectors.external_monitor_connectors.httpx.get") as g:
        g.return_value = mock.Mock(status_code=200, json=lambda: a, raise_for_status=lambda: None)
        da = conn.fetch_observations("q")[0]["raw_digest"]
        g.return_value = mock.Mock(status_code=200, json=lambda: b, raise_for_status=lambda: None)
        db = conn.fetch_observations("q")[0]["raw_digest"]
    assert da != db


def test_empty_query_fails_closed():
    conn = WigoloConnector(base_url="https://api.wigolo.test")
    with pytest.raises(ValueError):
        conn.fetch_observations("")


def test_missing_base_url_fails_closed():
    conn = WorldMonitorConnector()  # no base_url, default example placeholder
    with pytest.raises(ValueError):
        conn.fetch_observations("conflict-ukraine")


def test_http_error_fails_closed():
    conn = WorldMonitorConnector(base_url="https://api.worldmonitor.test")
    with mock.patch("valo_platform.speider_connectors.external_monitor_connectors.httpx.get") as g:
        g.return_value = mock.Mock(status_code=500, raise_for_status=mock.Mock(side_effect=Exception("500")))
        with pytest.raises(Exception):
            conn.fetch_observations("climate")


def test_malformed_payload_fails_closed():
    conn = WigoloConnector(base_url="https://api.wigolo.test")
    # not a dict with 'observations' list
    with mock.patch("valo_platform.speider_connectors.external_monitor_connectors.httpx.get") as g:
        g.return_value = mock.Mock(status_code=200, json=lambda: {"unexpected": 1}, raise_for_status=lambda: None)
        with pytest.raises(ValueError):
            conn.fetch_observations("acme")


def test_non_dict_observation_rejected():
    conn = WigoloConnector(base_url="https://api.wigolo.test")
    with mock.patch("valo_platform.speider_connectors.external_monitor_connectors.httpx.get") as g:
        g.return_value = mock.Mock(status_code=200, json=lambda: {"observations": ["not-a-dict"]}, raise_for_status=lambda: None)
        with pytest.raises(ValueError):
            conn.fetch_observations("acme")
