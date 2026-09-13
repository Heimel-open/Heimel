# External Production Proof

**Gate: one real third-party system through the same contract — nothing else.**

The internal vendor fixtures have proven the operator chain is vendor-neutral
structurally. This gate proves it EMPIRICALLY: swap the internal messaging
fixture for a REAL messaging vendor (real credentials, real endpoint, real
network boundary, actual external side effect, independent observation) and
run the SAME nine acceptance criteria.

## Hard requirement

> Switching from the internal vendor fixture to the third party must NOT require
> changing REHT, Operator, Function Fabric, Workflow ISA or Kernel. Only a
> `VendorConfig` (base_url + credentials) changes.

## Proof order

1. **Messaging / notification first** (low blast radius).
2. **Payments second** (stronger financial-consequence proof).

## The nine acceptance criteria (unchanged)

1. ALLOW -> actual external effect -> independently verified.
2. DENY -> zero external effect.
3. Revocation between plan and execution -> zero effect.
4. HTTP/API success without the desired state -> NOT verified.
5. Timeout/unknown outcome -> UNKNOWN, never synthetic success.
6. Retry/idempotency -> no double effect.
7. Changed action after permit -> permit invalid.
8. Full flow reconstructible from correlation_id + receipts.
9. Same Operator contract works with no adapter-side authorization.

## The deciding test

The deciding test is NOT the happy path. It is:

> Run the same notify submission through `ConfiguredGateway`/`ConfiguredVeritas`
> first against the internal messaging fixture, then against the real vendor —
> with the ONLY difference being a `VendorConfig` whose `base_url` and
> credentials come from environment variables. REHT, Operator, Function
> Fabric, Workflow ISA and Kernel are byte-identical.

## How to run (messaging first)

The harness `tests/test_external_proof.py` is gated on environment variables
read from the protected environment `external-production-proof`, provided ONLY
through a manual `workflow_dispatch` (`.github/workflows/external-proof.yml`) —
never automatically on push/PR, so CI can never accidentally send a real
message or consume the vendor account:

- `MSG_BASE_URL` — the real vendor API base, INCLUDING the account-specific
  path for the classic endpoint
  (e.g. `https://api.twilio.com/2010-04-01/Accounts/ACxxxx`).
- `MSG_FROM` — the verified sender identity.
- `MSG_AUTH` — the full `Authorization` header value, OR the API key + secret
  pair (`MSG_AUTH_USER` + `MSG_AUTH_SECRET`) from which the config builds
  `Basic base64(key:secret)`. Twilio recommends API key + secret.
- `recipient` — provided as the workflow input at dispatch time (never stored).

Twilio specifics are absorbed ENTIRELY in `VendorConfig` (never in the chain):
HTTP Basic auth, account-specific endpoint path, `content_type: form`
(`application/x-www-form-urlencoded`), `body_builder` (From/To/Body), and the
observation/status mapping (`status == "delivered"`). Vendor-neutral means the
external API's differences are absorbed by transport + observation config
without changing the governance architecture.

When the variables are absent the harness skips with a clear message. When
they are present it runs the notify flow through the REAL endpoint and asserts
all nine criteria, including the swap-without-code-change proof.

## Acceptance criterion (binary) for proof #1

```text
same Operator
same registered Function
same Function Fabric
same Workflow ISA
same Kernel
same REHT
same 9 proof invariants

ONLY VendorConfig changes
        |
        v
real external message
        |
        v
independently observed state
        |
        v
BARO VERIFIED
```

When green, mark it **External Production Proof #1**. Payments becomes proof
#2 with a far larger blast radius.

## Precision

The internal process/network boundary is already a **production-shaped proof**.
The FIRST third-party integration with real credentials and an actual external
side effect is the moment vendor neutrality becomes **empirically proven** —
not merely structurally claimed.

## Dependencies

- One real messaging account (credentials + a verified sender + a recipient).
- The operator repo CI or a local runner with network access to the vendor.

## Freeze note

Function Fabric `5b9b579` stays untouched behind the v1.2 gate. There is no
reason to open v1.2 until this external-production proof is in.
