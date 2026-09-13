# Work anchor — AADP and accountability convergence

Date: 2026-08-22
Owner: nsolland
Canonical base: 5e5bcdfac2a8dc7d3676ca10141ea4c73112d2e6
Branch: research/aadp-accountability-2026-08-22

Active delivery:
- record current IETF AADP convergence without changing REHT core semantics;
- adopt CAN/WHO/WHAT/AUDIT as an interoperability taxonomy, not a runtime dependency;
- add a negative non-bypass test for compromised containment plus alternate egress discovery;
- preserve the canonical execution chain and treat RACS as a binding contract, not a mandatory runtime hop.

Owned files:
- docs/adoption/IETF_AADP_ACCOUNTABILITY_2026-08-22.md
- tests/test_security_non_bypass_stage1.py
- docs/work-anchors/2026-08-22-aadp-accountability.md

Dependencies: existing RealReht, valo_gateway, containment gate, Veritas test fixtures.
