"""Council HTTP server — L6 human review endpoint.

Run standalone:
    COUNCIL_API_KEY=secret python -m vaig.council.server
"""

import os
import time
import logging

from flask import Flask, jsonify, request

from vaig.council.queue import CouncilQueue

app = Flask(__name__)
_queue = CouncilQueue()
_API_KEY = os.environ.get("COUNCIL_API_KEY", "")
_logger = logging.getLogger(__name__)


def _check_auth():
    if not _API_KEY:
        return None
    if request.headers.get("X-API-Key", "") != _API_KEY:
        return jsonify({"error": "unauthorized"}), 401
    return None


@app.post("/v5/council/submit")
def submit():
    err = _check_auth()
    if err:
        return err
    data = request.get_json(force=True) or {}
    item_id = _queue.submit_raw(
        level=data.get("level", "L3"),
        domain=data.get("domain", "UNKNOWN"),
        prompt=data.get("prompt", ""),
        response=data.get("response", ""),
        scores=data.get("scores", {}),
    )
    return jsonify({"id": item_id, "status": "queued"}), 201


@app.get("/v5/council/pending")
def pending():
    err = _check_auth()
    if err:
        return err
    return jsonify([i.as_dict() for i in _queue.pending()])


@app.post("/v5/council/verdict/<item_id>")
def verdict(item_id: str):
    err = _check_auth()
    if err:
        return err
    data = request.get_json(force=True) or {}
    decision = str(data.get("decision", "")).upper()
    try:
        ok = _queue.verdict(item_id, decision)
    except ValueError as e:
        _logger.warning("invalid council verdict for item %s: %s", item_id, e)
        return jsonify({"error": "invalid verdict"}), 400
    if not ok:
        return jsonify({"error": "item not found"}), 404
    return jsonify({"id": item_id, "verdict": decision, "ts": time.time()})


@app.get("/v5/council/stats")
def stats():
    return jsonify(_queue.stats())


@app.get("/v5/council/recent")
def recent():
    err = _check_auth()
    if err:
        return err
    limit = min(int(request.args.get("limit", 50)), 200)
    return jsonify([i.as_dict() for i in _queue.recent(limit)])


def run(port: int = 8083, debug: bool = False):
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    run()
