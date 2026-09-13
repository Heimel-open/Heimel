# VACS Integration Guide

**Status:** v0.1  
**Date:** 2026-06-25  
**Purpose:** Enable any repo to integrate VACS (VΛLΦ Agent Control Standard) protocol for identity-addressed governance messaging.

---

## What VACS Is

VACS is the canonical protocol for authority/policy/execution coordination across VΛLΦ ecosystem repos. It defines:

- **Identity attachment:** Unique identity (human, agent, system) bound to every decision
- **Policy binding:** Authority constraints explicitly stated before execution
- **Decision routing:** Standard vocabulary for routing decisions (ALLOW/STEP_UP/DEFER/DENY/HALT)
- **Receipt & audit trail:** Immutable proof that decision was made and executed
- **Integration contract:** How observation layers (BARO) feed decisions to execution gates (VAIG)

VACS is **not**:
- A replacement for VAIG (VAIG is L2 execution gate; VACS is the message protocol)
- A replacement for ACS (ACS is control model; VACS is coordination layer)
- A database schema (VACS is message envelope + decision routing)
- Real-time operational data (VACS carries governance signals, not telemetry)

---

## Visual Identity: VΛLΦ

VΛLΦ branding uses Greek letters:
- **V** = Latin V (decision/authority dimension)
- **Λ** = Greek Lambda (logic/execution dimension)
- **L** = Latin L (learning/measurement dimension)
- **Φ** = Greek Phi (proof/philosophy dimension)

The mix of Latin and Greek visually represents VΛLΦ's bridging role: connecting human authority (Latin/familiar) with mathematical rigor (Greek/formal).

---

## Core VACS Concepts

### Identity

Every VACS message includes identity information:

```json
{
  "identity": {
    "who": "arn:aws:iam::123456789:user/alice",
    "whom": "team/credit-risk",
    "whose": "acme-bank",
    "when": "2026-06-25T14:23:45Z",
    "where": "us-east-1",
    "audit_id": "audit_2026062514234567"
  }
}
```

- **Who:** Individual/service making the decision
- **Whom:** On behalf of which team/principal
- **Whose:** Whose authority is being delegated (org/customer/entity)
- **When:** Timestamp in UTC
- **Where:** Geographic/jurisdiction scope
- **Audit ID:** Unique trace for this decision across all systems

### Authority & Policy

Every VACS decision includes the authority context:

```json
{
  "authority": {
    "policy_id": "credit-approval-policy-v3",
    "policy_version": "3.2.1",
    "authority_scope": ["APPROVE", "BLOCK", "ESCALATE"],
    "delegated_by": "arn:aws:iam::123456789:role/credit-committee",
    "delegation_date": "2026-01-15",
    "expiry": "2026-12-31",
    "policy_excerpt": {
      "max_loan_amount": 250000,
      "max_approval_rate": 0.85,
      "escalation_threshold": 150000
    }
  }
}
```

- **Policy ID:** Unique identifier for governing policy
- **Policy Version:** Semantic versioning for audit trail
- **Authority Scope:** What decisions this identity is allowed to make
- **Delegated By:** Who granted this authority
- **Delegation Date / Expiry:** Time bounds on authority
- **Policy Excerpt:** Relevant constraints for this decision

### Decision & Execution

```json
{
  "decision": {
    "action": "APPROVE",
    "rationale": "Loan within policy bounds; borrower credit score 780",
    "confidence": 0.94,
    "cost_estimate": {
      "compute": "0.23",
      "human_review": "0",
      "risk_adjustment": "0.15"
    },
    "proof": {
      "hash": "sha256:abc123...",
      "signature": "sig:xyz789...",
      "timestamp": "2026-06-25T14:23:47Z"
    }
  }
}
```

- **Action:** ALLOW/STEP_UP/DEFER/DENY/HALT (standard vocabulary)
- **Rationale:** Why this decision was made
- **Confidence:** Model confidence (for ML decisions) or human confidence (for reviewed decisions)
- **Cost Estimate:** Pre-execution cost estimate (used by ROI Gate)
- **Proof:** Cryptographic proof (WORM receipt, signature)

### Routes & Outcomes

After execution, VACS carries outcome signal:

```json
{
  "outcome": {
    "executed": true,
    "execution_cost": {
      "compute": "0.19",
      "human_review": "0",
      "risk_realized": "0.08"
    },
    "value_created": 18500,
    "gain": {
      "formula": "(value_created - execution_cost) / authorization_cost",
      "ratio": 23.4,
      "confidence": "observed"
    },
    "audit_trail": "baro:2026062514234567→vaig:approve→execute:success→efficiency:measured"
  }
}
```

- **Executed:** True if action took place
- **Execution Cost:** Actual cost (vs. estimate)
- **Value Created:** Post-execution value measure
- **Gain:** Cost-benefit ratio and confidence level
- **Audit Trail:** Full chain of routing (BARO → VAIG → Execute → Efficiency Engine)

---

## Integration Pattern

### For Observation Layers (like BARO)

If you're building an observation layer that feeds signals to VALS gates:

```python
# 1. Generate observation signal
signal = {
    "source": "baro_narrative_radar",
    "signal_type": "ESCALATE",
    "domain": "energy_grid",
    "severity": "high",
    "context": {
        "description": "Grid topology churn accelerating; operator authority stable",
        "metric": "topology_churn_rate",
        "value": 8.3,
        "baseline": 2.1,
        "trend": "rising_5_days"
    }
}

# 2. Wrap in VACS identity
vacs_message = {
    "identity": vacs_identity(who="baro", whom="grid-ops", whose="tso-norway"),
    "signal": signal,
    "route": "vaig_escalation_handler"
}

# 3. Send to decision gate
response = vaig_client.evaluate(vacs_message)

# 4. Log the routing decision
audit_log.append({
    "source": "baro",
    "route_decision": response["action"],  # IGNORE, WATCH, ALERT, ESCALATE
    "confidence": response["confidence"],
    "audit_id": vacs_message["identity"]["audit_id"]
})
```

### For Execution Gates (like VAIG)

If you're building an execution gate that consumes VACS messages:

```python
class VACSGate:
    def evaluate(self, vacs_message):
        # 1. Extract identity & authority
        identity = vacs_message["identity"]
        authority = vacs_message["authority"]
        
        # 2. Verify authority is valid & non-expired
        assert self.verify_authority(authority), "Authority invalid"
        
        # 3. Extract decision & constraints
        decision = vacs_message["decision"]
        constraints = authority["policy_excerpt"]
        
        # 4. Pre-execute checks (ROI Gate, Authority Gate)
        roi_gate_result = self.roi_gate.evaluate(decision, constraints)
        auth_gate_result = self.authority_gate.evaluate(identity, authority)
        
        # 5. Route decision
        if roi_gate_result["action"] == "DENY":
            action = "DENY"
        elif auth_gate_result["action"] == "DENY":
            action = "DENY"
        else:
            action = "ALLOW"
        
        # 6. Execute and measure
        if action == "ALLOW":
            execution_result = self.execute(decision)
            outcome = {
                "executed": True,
                "execution_cost": execution_result["cost"],
                "value_created": execution_result["value"]
            }
        else:
            outcome = {
                "executed": False,
                "reason": f"{roi_gate_result['reason']} / {auth_gate_result['reason']}"
            }
        
        # 7. Return VACS response with proof
        return {
            "action": action,
            "confidence": decision["confidence"],
            "outcome": outcome,
            "proof": self.worm_logger.append({
                "vacs_id": vacs_message["identity"]["audit_id"],
                "action": action,
                "timestamp": utc_now()
            })
        }
```

### For Coordination (Index, Baro, VAIG, Landing)

**Level 1:** Repos agree on VACS identity format (who/whom/whose/when/where/audit_id)
**Level 2:** Repos map their route vocabulary to standard (ALLOW/STEP_UP/DEFER/DENY/HALT)
**Level 3:** Repos implement audit trail linking (source → route → execute → outcome)
**Level 4:** Cross-repo testing: BARO ESCALATE → VAIG ALLOW → Execute → Efficiency Engine measures

---

## VACS Conformance Checklist

For any repo integrating VACS, verify:

### Identity

- [ ] Every decision includes identity envelope (who/whom/whose/when/where)
- [ ] Audit ID is unique and globally traceable
- [ ] Identity can be cryptographically verified (signatures, PKI integration)
- [ ] Identity is immutable once written to audit log

### Authority

- [ ] Authority is bound to identity (not assumed from context)
- [ ] Authority scope is explicit (list of allowed actions)
- [ ] Authority has expiry date
- [ ] Policy version is recorded with decision
- [ ] Policy constraints are enforced pre-execution (not post-hoc)

### Decision

- [ ] Action is from standard vocabulary (ALLOW/STEP_UP/DEFER/DENY/HALT)
- [ ] Rationale is recorded (why this decision was made)
- [ ] Confidence score is present
- [ ] Pre-execution cost estimate is recorded
- [ ] Signature/proof is cryptographically valid

### Execution & Outcome

- [ ] Execution is conditional on decision (ALLOW → execute, DENY → don't execute)
- [ ] Execution cost is measured and recorded
- [ ] Post-execution value is measured and recorded
- [ ] Gain is calculated (value - cost) with confidence level
- [ ] Audit trail links all steps (decision → execution → outcome)

### Audit

- [ ] WORM log contains decision + execution + outcome
- [ ] Hash chain is unbroken (each entry references previous)
- [ ] Audit trail is immutable (read-only log, no post-hoc edits)
- [ ] Audit ID matches across all systems (BARO → VAIG → Execute → Efficiency Engine)
- [ ] Decision Trace can be reconstructed (who/what/authority/policy/execute/consequence)

---

## Deployment Stages

**Stage 1 (Bootstrap):** Identity + Authority binding
- Integrate VACS identity envelope into existing decision points
- Add authority validation before execution
- Implement WORM audit log for decisions

**Stage 2 (Routing):** Decision vocabulary standardization
- Map existing route/decision logic to ALLOW/STEP_UP/DEFER/DENY/HALT
- Add pre-execution gates (ROI Gate, Authority Gate)
- Implement cross-repo routing (BARO → VAIG → Execute)

**Stage 3 (Measurement):** Outcome tracking
- Add post-execution cost measurement
- Add value creation measurement
- Calculate gain ratio and confidence

**Stage 4 (Optimization):** Learning & feedback
- Use outcome data to improve policy
- Use gain ratios to optimize resource allocation
- Use audit trail for incident analysis

---

## Example: Credit Approval Workflow (Banking)

```
Human (VP of Credit) decides: "Approve $50K loan to Acme Corp"
    ↓
VACS Identity: who=vpxyz, whom=credit-team, whose=acme-bank, when=2026-06-25T14:30:00Z
    ↓
Authority Check: VP Credit has authority to approve $50K (policy limit $250K)
    ↓
ROI Gate: Estimated value $8K (interest margin) > cost $0.15 (review time)
    ↓
Execute: Loan approved, funds wired
    ↓
Outcome: Loan approved. Value: $8K. Cost: $0.12. Gain: 66.7x
    ↓
WORM Log: Decision + Execution + Outcome stored immutably
    ↓
Audit Trail: Who decided? VP Credit. What policy? $250K limit. What happened? Approved & wired. Did we gain? Yes, 66.7x.
```

---

## FAQs

**Q: Does VACS replace VAIG?**  
A: No. VAIG is the execution gate (decides ALLOW/DENY). VACS is the message protocol that carries decisions between BARO, VAIG, and efficiency engines.

**Q: Can I use VACS without WORM?**  
A: Technically yes, but the audit trail loses cryptographic proof. For regulated deployments, WORM audit is required.

**Q: Does VACS work for non-AI delegations (contractors, humans, board decisions)?**  
A: Yes. VACS is delegation-agnostic. The identity/authority/decision/outcome pattern applies to any delegated work.

**Q: What's the latency impact of VACS?**  
A: VACS message construction + routing: <10ms. WORM hash chain: <5ms. Total overhead should stay <50ms for real-time use cases. VΛLΦ L1 gate guarantees 43ns decision latency; VACS routing adds <100ms for cross-repo coordination.

**Q: How do I integrate with repos that don't speak VACS yet?**  
A: Stage 1: Wrap their decisions in VACS envelope at boundary. Stage 2: Request they adopt VACS natively. Use bridging layers until full adoption.

**Q: Is VACS related to VΛLΦ branding?**  
A: Yes. VACS is the technical protocol. VΛLΦ is the brand. VACS is what it does. VΛLΦ is who we are.

---

## References

- VAIG Authority Gate: `nsolland/vaig/docs/authority-gate.md`
- ROI Gate: `nsolland/vaig/docs/VALO_ROI_GATE_IMPLEMENTATION_2026-06-24.md`
- BARO VACS Handoff: `nsolland/Baro/docs/BARO_VACS_HANDOFF.md`
- ACS/VACS Boundary: `nsolland/vaig/docs/ACS_VACS_CONFORMANCE.md`
- Decision Trace: `nsolland/Index/projects/valo-as/operational-principle-decision-trace.md`

