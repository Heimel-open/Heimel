# Build Order: LastSeen MVP

Status: IMPLEMENTED IN `feat/lastseen-mvp`
Owner: VALO Edge
Repository: `nsolland/valo-edge`
Canonical base: `1faf2b3fe6e94bc77d790d78c3234a84362ddd3f`

## Outcome

Deliver a useful local object-memory product that can be demonstrated without a camera integration. A local detector or a human can submit structured observations. LastSeen stores, retrieves and deletes them only after micro-REHT clearance and emits Veritas receipts.

## Owned files

- `src/valo_edge/lastseen/**`
- `tests/test_lastseen.py`
- `site/**`
- `docs/lastseen/**`
- `.github/workflows/lastseen-*.yml`
- LastSeen sections in `README.md` and `pyproject.toml`

## MVP contract

Input observation:

```json
{
  "object_name": "keys",
  "location": "kitchen counter, beside the coffee machine",
  "image_ref": "crops/keys-kitchen.jpg",
  "confidence": 0.98,
  "observed_at_iso": "2026-08-04T08:42:00Z"
}
```

Required actions:

- `STORE_OBSERVATION`
- `READ_LAST_SEEN`
- `DELETE_OBJECT_HISTORY`

Every action must pass through:

`proposal -> micro-REHT -> local operation -> gateway -> Veritas receipt`

## Acceptance gates

- `lastseen remember` stores one local observation.
- `lastseen find` returns the newest matching observation.
- Aliases can resolve a query to a known object.
- `lastseen forget` removes an object's complete history.
- Invalid observations fail before storage.
- Each successful consequence returns a 64-character receipt digest.
- SQLite is the only persistence dependency.
- No network call is required.
- The static website works without a backend.
- Unit tests pass on Python 3.10, 3.11 and 3.12.

## Demo command

```bash
python -m pip install -e ".[dev]"
lastseen --db /tmp/lastseen.db demo
```

Expected visible result:

```text
Where are my keys?
Last seen: kitchen counter, beside the coffee machine at 2026-08-04T08:42:00Z
Local receipt: <sha256>
No video left the device.
```

## Explicit non-goals

- No face recognition.
- No person tracking.
- No cloud inference.
- No permanent raw-video archive.
- No autonomous camera configuration.
- No claim that the MVP proves production-grade privacy or security.
