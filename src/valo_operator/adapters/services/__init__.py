"""Standalone external services. Each runs as its OWN process with its OWN
state — the Operator talks to them over real HTTP. They are real effect points:
a notification record / a ledger entry lives in the service's state, and
Veritas verifies it by reading that state back, independently of the send."""
