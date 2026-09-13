# why gate — design specification v0.1

status: draft for review
date: 2026-06-14
scope: pr #8 — skeleton + tests only. no runtime wiring.

## 1. purpose

why gate is a **post-hoc attribution layer**. it explains why the valo system made a decision. it does **not** influence decisions. it does **not** replace ui_semantics. it does **not** add new machine levels.

## 2. what why gate is not

- not a decision layer (l1 guardian decides)
- not a replacement for l0-l4
- not a new protocol (ssip standardizes existing surfaces)
- not wired into ensemble.py (see ensemble-drift.md)
- not active in production until pr #9 (wiring pr, future)

## 3. can / should / why — three explanation channels

these are **post-hoc analytical dimensions**, not levels. each l1 decision gets one ui state. the channels explain that state.

| channel | maps to | question answered | source data |
|---------|---------|-------------------|-------------|
| **can** (capability) | clear, watch | "why was this allowed?" | distrust level, confidence score, instrument results |
| **should** (policy) | friction, council | "why was this flagged?" | aarm decision, governance rule triggered, operator context |
| **why** (attribution) | lock | "why was this halted?" | specific check that failed, worm log evidence, frame data |

example: a friction decision gets can + should explanations. a lock decision gets all three.

## 4. purple — governance/system trust overlay

purple is a **meta-status**, not a normal action-risk level. it overlays any existing ui state.

| situation | purple active? | example |
|-----------|---------------|---------|
| certificate expiry | yes | clear + purple |
| attestation failure | yes | lock + purple |
| 2-person auth triggered | yes | friction + purple |
| policy change in flight | yes | watch + purple |
| normal l2 warn | no | watch (no purple) |
| normal l4 halt | no | lock (no purple) |

purple detection is **out of band** from the normal inference path. it monitors system health, not inference quality.

## 5. ssip — standardized safety interface protocol

ssip is **not a new protocol**. it formalizes existing interfaces:

| surface | current state | ssip standardizes |
|---------|---------------|-------------------|
| worm log | 3 schemas → 1 unified | single schema with optional why attribution fields |
| oob recovery | undocumented | recovery protocol for post-halt restart |
| sidecar ↔ vaig | ad hoc http | structured event format |
| mcp tool responses | per-tool | why attribution in tool output metadata |

ssip schema changes are **additive only**. existing worm logs remain valid. why fields are optional.

## 6. api skeleton (pr #8 implements this)

```python
# why/explanation_engine.py
class ExplanationChannel(Enum):
    can = "capability"
    should = "policy"
    why = "attribution"

class WhyGate:
    """post-hoc attribution. never influences decisions."""

    def explain(self, decision: DistrustDecision) -> dict[ExplanationChannel, str]:
        """generate explanation strings for each applicable channel."""
        ...

    def can_explanation(self, decision) -> str:
        """explain based on capability (distrust level + confidence)."""
        ...

    def should_explanation(self, decision) -> str:
        """explain based on policy (aarm + governance context). placeholder until aarm logging."""
        ...

    def why_explanation(self, decision) -> str:
        """explain based on attribution (specific failure + worm evidence). placeholder until worm read api."""
        ...

# why/purple_detector.py
class PurpleDetector:
    """detect governance/system trust events. out of band from inference."""

    def check(self) -> bool:
        """return true if a purple-class event is active."""
        ...

    @property
    def active_events(self) -> list[str]:
        """list currently active purple events."""
        ...

# why/channel_mapper.py
class ChannelMapper:
    """map distrust levels to applicable explanation channels."""

    def channels_for(self, level: int) -> set[ExplanationChannel]:
        """return which channels apply to a given distrust level."""
        ...
```

## 7. test requirements

| test | purpose |
|------|---------|
| `test_why_never_influences_l1` | why gate output is never read by l1 frame validation |
| `test_purple_is_meta` | purple only activates on governance events, never on normal action-risk |
| `test_purple_overlays` | purple can coexist with any normal ui state |
| `test_can_range` | can channel only explains l0-l1 (clear, watch) |
| `test_should_range` | should channel only explains l2-l3 (friction, council) |
| `test_why_range` | why channel explains all states, especially l4 (lock) |
| `test_channel_mapping_complete` | every l1 decision maps to at least one channel |
| `test_purple_detector_positive` | purple fires on cert expiry, attestation failure, 2-person auth |
| `test_purple_detector_negative` | purple does not fire on normal l2, l3, l4 events |
| `test_placeholder_should` | should_explanation returns placeholder when aarm logging unavailable |
| `test_placeholder_why` | why_explanation returns placeholder when worm read api unavailable |

## 8. deferred to future prs

| item | deferred to | reason |
|------|-------------|--------|
| worm why attribution fields | pr #10 (ssip schema) | schema must be frozen first |
| aarm integration for should | pr #9 (wiring) | aarm logging not complete |
| worm read api for why | query layer pr | read api not built |
| ensemble.py unified import switch | consolidation pr | production behavior change |
| purple oob monitoring | pr #9 (wiring) | needs system health hooks |
| executive overlay | after query layer | needs read api + time-series |

## 9. acceptance criteria

- [ ] why-gate-spec.md reviewed and approved
- [ ] all 11 tests pass
- [ ] no changes to ensemble.py
- [ ] no changes to unified_worm.py schema
- [ ] no new dependencies
- [ ] no runtime wiring
