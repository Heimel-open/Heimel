# VALO Proxy

Thin governance layer for any AI backend. Three files, no ML dependencies.

Point your AI client at `localhost:8082` instead of the backend. Every request is gated and logged.

```
Your App → VALO Proxy :8082 → Any AI Backend
                ↓
         WORM Audit Log (SHA-256 hash-chained)
```

## Install

```bash
pip install flask flask-cors
```

## Run

```bash
VALO_COHERENCE_THRESHOLD=<C0>           \
VALO_BACKEND_URL=https://api.anthropic.com  \
VALO_BACKEND_API_KEY=sk-ant-...         \
python -m proxy.proxy
```

Works with any backend: Anthropic, OpenAI, Azure OpenAI, ollama, or any HTTP inference server.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `VALO_COHERENCE_THRESHOLD` | **required** | Gate threshold (C₀) |
| `VALO_BACKEND_URL` | **required** | Backend base URL |
| `VALO_BACKEND_API_KEY` | — | Forwarded as Bearer token |
| `VALO_PROXY_PORT` | `8082` | Listen port |
| `VALO_DEFAULT_CONFIDENCE` | `0.85` | Default confidence score |
| `VALO_WORM_LOG` | `~/.valo-proxy/worm.jsonl` | Audit log path |

## Per-request confidence

```
X-Valo-Confidence: 0.95
```

## Gate outcomes

| Status | Meaning |
|---|---|
| `PASS` | Request forwarded |
| `DEGRADE` | Request forwarded, flagged in log |
| `HALT` | Request blocked, 503 returned |

## Audit log

```bash
curl http://localhost:8082/v5/proxy/worm/tail?n=10
```

The log at `~/.valo-proxy/worm.jsonl` is SHA-256 hash-chained.
Tampering with any entry breaks the chain.

Built by [VALO Research Group](https://valoresearch.org). LIM — Law of Identity Maintenance.
