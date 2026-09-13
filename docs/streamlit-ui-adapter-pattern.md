# Streamlit UI Adapter Pattern

Status: adopted pattern for rapid internal/demo surfaces. Not a core dependency.

## Purpose

Use Streamlit as a replaceable presentation adapter when VALO capabilities need a fast interactive web surface without introducing a separate frontend stack.

Typical uses:

- governed-workspace demonstrations
- shadow-mode dashboards
- Factory/operator cockpits
- EMOS / CEO Game prototypes
- receipt, state, decision and scenario inspection
- small operational tools in front of Packs and Factory functions

## Architectural boundary

Streamlit is presentation only. It does not become part of the VALO authorization boundary and it receives no execution authority from UI interaction.

Canonical interaction:

```text
governed state / read model
        |
        v
Streamlit presentation adapter
        |
        | user interaction produces candidate intent
        v
VALO governed execution path
VAIG -> reht -> RACS -> external PEP/Gateway -> execution -> Veritas receipt
```

A button press, form submit, session state value, token or Streamlit callback MUST NOT itself authorize an action.

## Invariants

1. Streamlit remains replaceable. Core contracts MUST NOT depend on Streamlit types, lifecycle or session semantics.
2. Read surfaces consume bounded governed state or explicit projections, not unrestricted enterprise state.
3. UI-originated changes are candidate intents only until admitted by the normal governed execution path.
4. Authorization is evaluated at execution time; cached UI state cannot preserve authority.
5. Fail closed when required authority, provenance, purpose, evidence or current state is unavailable.
6. Receipts and authoritative state are produced outside the presentation adapter.
7. Hidden retries, automatic promotion and UI-local bypasses are prohibited.

## Adoption rule

Prefer this pattern for rapid prototyping and internal/operator surfaces where speed of comprehension matters more than bespoke frontend engineering. Replace it with another UI technology without changing VALO contracts when product requirements demand it.

## Non-goals

This pattern does not make Streamlit:

- an execution gateway
- a PEP
- an authority source
- a source of governed truth
- a required runtime dependency for VALO core

## Source signal

Adopted after reviewing Streamlit as a Python-native route to interactive web applications. The useful signal is delivery speed, not architectural authority: VALO can expose governed capabilities quickly while keeping the presentation layer disposable.
