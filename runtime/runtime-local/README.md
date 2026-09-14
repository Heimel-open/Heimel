# valo-runtime-local

Offline reference implementation of the Heimel governed consequence path.

The local runtime does not execute on submit and cannot report SUCCESS until the exact effect has passed the full local path:

```text
proposed action
-> fresh authority check
-> exact decision/effect binding
-> one-shot permit enforcement
-> local effect
-> attributable evidence receipt
```

The reference implementation is self-contained: no vendor API, Heimel cloud account, phone-home or license server is required.

Fail-closed properties covered by integration tests:

- DENY cannot become effect
- revocation invalidates an already issued permit
- expired permits cannot execute
- effect mismatch cannot execute
- permits cannot be replayed
- PENDING actions cannot report SUCCESS
- an effect whose evidence recording fails remains `EFFECT_OCCURRED_UNATTESTED` and cannot be admitted as SUCCESS

Run locally from this directory:

```bash
pytest -q
```
