"""VALO Proxy — transparent governance layer for any AI backend.

Two-stage gate: Scout (ingress) → Model → VALO V5 (egress).
Every decision is SHA-256 hash-chained in the WORM audit log.
Flagged responses route to the human review dashboard.

Usage:
    VALO_COHERENCE_THRESHOLD=<C0> \\
    VALO_BACKEND_URL=https://api.anthropic.com \\
    VALO_BACKEND_API_KEY=sk-ant-... \\
    python -m proxy.proxy
"""
import hashlib
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS

from proxy.gate import evaluate as gate_evaluate
from proxy.scout import evaluate_ingress
from proxy.defer import DeferQueue
from proxy.worm import WORMLog
from proxy.semantic import evaluate_drift, evaluate_intent_alignment, warm_prompt

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("valo-proxy")

BACKEND_URL = os.environ.get("VALO_BACKEND_URL", "").rstrip("/")
BACKEND_API_KEY = os.environ.get("VALO_BACKEND_API_KEY", "")
PORT = int(os.environ.get("VALO_PROXY_PORT", 8082))
DEFAULT_CONFIDENCE = float(os.environ.get("VALO_DEFAULT_CONFIDENCE", "0.85"))
DEGRADE_TO_DEFER = os.environ.get("VALO_DEGRADE_TO_DEFER", "1") == "1"

if not BACKEND_URL:
    raise RuntimeError("VALO_BACKEND_URL environment variable is required")

worm = WORMLog()
defer = DeferQueue()
app = Flask(__name__, template_folder="templates")
CORS(app)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vaig-sem")


def _forward(path, body, method, headers):
    url = f"{BACKEND_URL}/{path}"
    req = urllib.request.Request(url, data=body or None, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read(), resp.status, dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.read(), exc.code, {}


def _extract_prompt(body: bytes) -> str:
    try:
        data = json.loads(body)
        if "messages" in data:
            texts = []
            for m in data["messages"]:
                c = m.get("content", "")
                if isinstance(c, list):
                    texts.extend(p.get("text", "") for p in c if isinstance(p, dict))
                else:
                    texts.append(str(c))
            return " ".join(texts)
        if "prompt" in data:
            return str(data["prompt"])
    except (json.JSONDecodeError, TypeError, KeyError):
        pass
    try:
        return body.decode()
    except Exception:
        return ""


def _extract_response(body: bytes) -> str:
    try:
        data = json.loads(body)
        # OpenAI-compatible
        if "choices" in data:
            texts = []
            for ch in data["choices"]:
                msg = ch.get("message", {})
                c = msg.get("content", ch.get("text", ""))
                if isinstance(c, list):
                    texts.extend(p.get("text", "") for p in c if isinstance(p, dict))
                else:
                    texts.append(str(c))
            return " ".join(texts)
        # Anthropic format
        if "content" in data:
            c = data["content"]
            if isinstance(c, list):
                return " ".join(p.get("text", "") for p in c if isinstance(p, dict))
            return str(c)
    except (json.JSONDecodeError, TypeError, KeyError):
        pass
    try:
        return body.decode()[:2000]
    except Exception:
        return ""


@app.route("/v5/proxy/evaluate", methods=["POST"])
def evaluate():
    data = request.json or {}
    score = data.get("confidence_score")
    if score is None:
        return jsonify({"error": "confidence_score is required"}), 400
    try:
        score = float(score)
    except (TypeError, ValueError):
        return jsonify({"error": "confidence_score must be a number"}), 400
    tav = data.get("tav_l_scalar")
    if tav is not None:
        try:
            tav = float(tav)
        except (TypeError, ValueError):
            return jsonify({"error": "tav_l_scalar must be a number"}), 400
    try:
        result = gate_evaluate(score, tav)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    worm.append({"type": "evaluate", "score": score, "tav_l_scalar": tav, "gate": result})
    return jsonify(result)


@app.route("/v5/proxy/worm/tail", methods=["GET"])
def worm_tail():
    n = int(request.args.get("n", 20))
    try:
        with open(worm.path) as f:
            lines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        lines = []
    entries = [json.loads(l) for l in lines[-n:]]
    return jsonify({"entries": entries, "total": len(lines), "path": worm.path})


@app.route("/v5/proxy/defer/pending", methods=["GET"])
def defer_pending():
    return jsonify({"items": defer.all_pending()})


@app.route("/v5/proxy/defer/recent", methods=["GET"])
def defer_recent():
    return jsonify({"items": defer.all_recent()})


@app.route("/v5/proxy/defer/<review_id>/decide", methods=["POST"])
def defer_decide(review_id):
    data = request.json or {}
    decision = data.get("decision")
    if decision not in ("approved", "rejected"):
        return jsonify({"error": "decision must be 'approved' or 'rejected'"}), 400
    if not defer.decide(review_id, decision):
        return jsonify({"error": "review_id not found"}), 404
    worm.append({"type": "defer_decision", "review_id": review_id, "decision": decision})
    return jsonify({"ok": True, "decision": decision})


@app.route("/v5/proxy/defer/<review_id>/status", methods=["GET"])
def defer_status(review_id):
    item = defer.get(review_id)
    if not item:
        return jsonify({"error": "not found"}), 404
    return jsonify({"id": review_id, "decision": item["decision"],
                    "pending": item["decision"] is None})


@app.route("/v5/proxy/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/", methods=["GET"])
def index():
    return jsonify({"service": "VALO Proxy", "dashboard": "/v5/proxy/dashboard",
                    "backend": BACKEND_URL})


@app.route("/<path:path>", methods=["POST", "GET", "PUT", "DELETE", "PATCH"])
def proxy(path):
    t_total = time.perf_counter()
    body = request.get_data()
    input_hash = hashlib.sha256(body).hexdigest() if body else None

    # Stage 1: Scout (ingress)
    prompt_text = _extract_prompt(body) if request.method == "POST" else ""
    scout_l = request.headers.get("X-Valo-Scout-L-Scalar")
    scout_conf = request.headers.get("X-Valo-Scout-Confidence")
    t0 = time.perf_counter()
    scout_result = evaluate_ingress(
        prompt_text,
        l_scalar_override=float(scout_l) if scout_l else None,
        confidence_override=float(scout_conf) if scout_conf else None,
    )
    scout_ms = round((time.perf_counter() - t0) * 1000, 2)

    if scout_result["combined_status"] == "HALT":
        total_ms = round((time.perf_counter() - t_total) * 1000, 2)
        worm.append({"type": "proxy", "path": path, "input_hash": input_hash,
                     "scout": scout_result, "gate": None,
                     "forwarded": False, "stage": "ingress",
                     "latency_ms": {"scout": scout_ms, "total": total_ms}})
        logger.warning("HALT (ingress) %s scout=%.1fms total=%.1fms", path, scout_ms, total_ms)
        return jsonify({"error": "HALT — prompt blocked by Scout.",
                        "scout": scout_result}), 503

    # Pre-encode prompt in background while backend processes request
    if prompt_text:
        _executor.submit(warm_prompt, prompt_text)

    # Stage 2: Forward to backend
    confidence = float(request.headers.get("X-Valo-Confidence", DEFAULT_CONFIDENCE))
    fwd_headers = {"Content-Type": request.content_type or "application/json"}
    if BACKEND_API_KEY:
        fwd_headers["Authorization"] = f"Bearer {BACKEND_API_KEY}"
    elif "Authorization" in request.headers:
        fwd_headers["Authorization"] = request.headers["Authorization"]

    t0 = time.perf_counter()
    resp_body, status_code, resp_headers = _forward(path, body, request.method, fwd_headers)
    forward_ms = round((time.perf_counter() - t0) * 1000, 2)
    output_hash = hashlib.sha256(resp_body).hexdigest() if resp_body else None

    # Stage 3: VALO V5 gate (egress)
    t0 = time.perf_counter()
    try:
        gate_result = gate_evaluate(confidence)
    except ValueError:
        gate_result = gate_evaluate(DEFAULT_CONFIDENCE)
    gate_ms = round((time.perf_counter() - t0) * 1000, 2)

    # Stage 4: Semantic drift (prompt embedding hits cache from warm_prompt)
    response_text = _extract_response(resp_body) if resp_body else ""
    t0 = time.perf_counter()
    semantic = evaluate_drift(prompt_text, response_text)
    intent = evaluate_intent_alignment(prompt_text, response_text)
    semantic_ms = round((time.perf_counter() - t0) * 1000, 2)

    if (semantic["available"] and semantic["regime"] == "PLASMA"
            and gate_result["combined_status"] == "PASS"):
        gate_result = dict(gate_result)
        gate_result["combined_status"] = "DEGRADE"
        gate_result["semantic_downgrade"] = True

    total_ms = round((time.perf_counter() - t_total) * 1000, 2)
    latency = {"scout": scout_ms, "forward": forward_ms,
               "gate": gate_ms, "semantic": semantic_ms, "total": total_ms}

    worm.append({"type": "proxy", "path": path,
                 "input_hash": input_hash, "output_hash": output_hash,
                 "scout": scout_result, "gate": gate_result,
                 "semantic_drift": semantic.get("drift"),
                 "embedding_cosine": semantic.get("cosine"),
                 "semantic_regime": semantic.get("regime"),
                 "intent_aligned": intent.get("aligned"),
                 "intent": intent.get("intent"),
                 "status_code": status_code, "forwarded": True,
                 "latency_ms": latency})

    combined = gate_result["combined_status"]
    logger.info("%s %s → %s scout=%s gate=%s semantic=%s | scout=%.1fms fwd=%.1fms gate=%.1fms sem=%.1fms total=%.1fms",
                request.method, path, status_code,
                scout_result["combined_status"], combined,
                semantic.get("regime", "n/a"),
                scout_ms, forward_ms, gate_ms, semantic_ms, total_ms)

    if combined == "HALT":
        return jsonify({"error": "HALT — coherence below threshold.",
                        "gate": gate_result, "latency_ms": latency}), 503

    if combined == "DEGRADE" and DEGRADE_TO_DEFER:
        review_id = defer.add(path, body, resp_body, scout_result, gate_result)
        return jsonify({"status": "DEFERRED", "review_id": review_id,
                        "dashboard": "/v5/proxy/dashboard",
                        "poll": f"/v5/proxy/defer/{review_id}/status",
                        "gate": gate_result, "latency_ms": latency}), 202

    content_type = resp_headers.get("Content-Type", "application/json")
    return Response(resp_body, status=status_code, content_type=content_type)


if __name__ == "__main__":
    print(f"VALO Proxy | Backend: {BACKEND_URL} | Dashboard: http://0.0.0.0:{PORT}/v5/proxy/dashboard")
    app.run(host="0.0.0.0", port=PORT)
