# WORM Audit Guarantees

Status: implemented and tested  
File: `vaig/worm.py`  
Tests: `tests/test_worm.py`

## What WORM means here

WORM = Write-Once-Read-Many.

In this implementation it means: entries can only be appended, never modified in place. Any modification to a past entry breaks the hash chain and is detectable by `verify()`.

## Hash chain construction

Every entry is a JSON object with the following structure:

```json
{
  "id": "entry-id",
  "ts": 1750000000.0,
  "prev": "<sha256-of-previous-entry>",
  "<custom-fields>": "...",
  "prompt_sha256": "<sha256-of-prompt>",
  "response_sha256": "<sha256-of-response>",
  "hash": "<sha256-of-this-entry-without-hash-field>"
}
```

Chain invariant:
- `entry["prev"]` == `hash` of the immediately preceding entry
- `entry["hash"]` == SHA-256 of the entry JSON (sorted keys, `hash` field excluded before hashing)
- First entry: `prev` = `"genesis"`

Any edit to any past entry changes its JSON, changes its SHA-256, breaks the chain from that point forward.

## Append-only enforcement

The WORM log uses two layers of append-only enforcement:

1. **In-process threading lock** — `threading.Lock()` prevents concurrent writes from the same process.
2. **OS-level file lock** — `fcntl.LOCK_EX` prevents concurrent writes from multiple processes on the same host.
3. **fsync after write** — each entry is flushed to disk before the lock is released.

Append-only is enforced at the OS level for same-host deployments. It is not enforced at the hardware or network storage level.

## Tamper detection

```python
worm = WORMLog("audit.jsonl")
is_intact = worm.verify()
```

`verify()` walks the full chain from genesis, recomputes every hash, and checks that `entry["prev"]` matches the previous entry's hash. Returns `True` only if all entries are intact and sequentially linked.

## Encryption (Level 2)

When an `encryption_key` is provided, prompt and response content is encrypted using XOR with a SHA-256-derived key stream:

```python
worm = WORMLog("audit.jsonl", encryption_key=os.urandom(32))
```

**Important limits of current encryption:**

- XOR with a repeated key stream is not AES-256 or any standardized cipher.
- It is not suitable for adversarial environments, regulatory storage, or long-term confidentiality claims.
- Its purpose in this implementation is to demonstrate the *architecture* of customer-key separation: the audit log stores encrypted blobs; the plaintext is only recoverable by the holder of the key.
- For production regulated deployments, replace with AES-256-GCM or equivalent.

Level 1 (SHA-256 hashes of prompt + response) is always active regardless of encryption. SHA-256 of content proves integrity without storing or exposing the content.

## Storage backend

- Current: filesystem JSONL file on local disk.
- The implementation does not use hardware locking, tamper-resistant storage, HSM, or distributed consensus.
- For production Annex III deployments, the storage backend should be replaced with:
  - hardware-locked NVMe (as referenced in valo-v5-core)
  - or append-only cloud storage with server-side integrity verification

## Failure modes

| Failure | Effect |
|---|---|
| Single entry modified | `verify()` returns False from that entry onward |
| Entry deleted | Chain break: next entry's `prev` will not match |
| Log file truncated | Chain terminates early; `verify()` returns True for remaining entries |
| Process crash during write | Partial write possible; last line may be corrupt JSON — `verify()` will fail cleanly on that line |
| Two processes writing simultaneously | Protected by `fcntl.LOCK_EX` on same host; not protected across network mounts |

## Replay and rebuild

No replay / rebuild procedure is currently implemented. Chain integrity is verified forward from genesis only. There is no reverse-lookup or branch-detection mechanism.

To rebuild from backup: restore the JSONL file and run `verify()`. If `verify()` returns True, the chain is intact from genesis to current tail.

## What this implementation proves

Allowed claims from this implementation:

- SHA-256 hash-chain construction is implemented and tested
- Tamper detection via `verify()` is implemented and tested
- Append-only behavior is enforced at the process and OS level for same-host deployments
- Encrypted content storage (customer-holds-key architecture) is implemented

Not allowed to claim:

- Hardware-locked tamper-resistant storage
- AES-256 content encryption
- Distributed or replicated audit trail
- Annex III compliant storage (storage backend must be hardened before use in regulated deployment)
- Guarantee against OS-level tampering by a privileged process

## Test reference

`tests/test_worm.py` covers:

- append and verify (intact chain)
- tamper detection (modified entry breaks verify)
- encrypted append and decrypt
- multi-entry chain
- thread-safe concurrent appends (same process)

Run: `pytest tests/test_worm.py -v`
