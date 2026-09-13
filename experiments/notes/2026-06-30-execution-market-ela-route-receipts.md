# From model market to execution market

Date: 2026-06-30
Status: draft / research note
Maturity: M1 conceptual, with possible M2 architecture path

Note: This preserves the argument as a working draft. Claims about recent reporting, research and route-receipt literature should be source-verified before publication.

---

I think you’re pointing at something bigger than token pricing.

2027 may become the year when AI shifts from a model market to an execution market.

Today we buy access to models.

Tomorrow we’ll buy execution quality.

Those are not the same thing.

Imagine buying a Ferrari.

You don’t actually care whether the engine is capable of 800 horsepower.

You care whether today’s trip was driven with all 800 horsepower, or whether the ECU silently limited it to 250 because the manufacturer decided your road didn’t require more.

That’s exactly where AI is heading.

Every provider has enormous economic incentives to reduce inference cost.

Not by making models worse.

By making execution adaptive.

For every request they can choose:

- Which model?
- How much reasoning?
- How many planning iterations?
- Which tools?
- Which context?
- Which safety pipeline?
- Which GPU cluster?
- Which latency target?
- Which customer tier?

The customer only sees:

```text
Claude answered.
```

or

```text
GPT answered.
```

That abstraction worked when AI was mostly chat.

It breaks when enterprises begin spending millions on inference. Recent reporting already shows enterprises moving toward dynamic routing, cheaper models for simpler work, and AI cost governance because inference spend is becoming a major financial issue.

I think a new layer emerges.

Today we have:

```text
Model Card
-> describes the trained model.
```

Tomorrow we’ll need:

```text
Execution Card / Route Receipt
-> describes the execution path that produced a specific answer.
```

For every important answer:

- Model family
- Runtime model
- Model version
- Compute tier
- Reasoning budget
- Context size
- Active policies
- Active safety constraints
- Tool chain
- Routing decisions
- Confidence
- Cryptographic signature

Now the customer knows what they actually bought.

---

## Economic point

Today the provider captures almost all efficiency gains.

If they discover a way to answer your question with one-third the compute, they keep the margin.

But enterprise customers will eventually ask:

```text
I paid for Premium AI. Did I actually receive Premium AI?
```

That question is impossible to answer today.

It becomes even harder because agentic workloads are far more expensive and more variable than ordinary chat. Recent research finds that identical agentic tasks can vary dramatically in token consumption between runs, and higher token use does not necessarily produce better outcomes.

That leads to the next enterprise requirement:

```text
SLA: Service Level Agreement
ELA: Execution Level Agreement
```

An ELA would specify things like:

- Minimum reasoning budget
- Maximum routing degradation
- Guaranteed model family
- Maximum fallback probability
- Governance policy version
- Verifiable execution receipt

Now procurement changes completely.

Instead of buying:

```text
GPT-6 Enterprise
```

a bank buys:

```text
Tier-A Execution:
- No fallback
- Minimum reasoning budget X
- Maximum latency Y
- Signed execution receipt
- Full audit trail
```

That’s measurable.

It’s also auditable.

---

## Link to route receipts and VALO

Recent work has proposed route receipts as a runtime transparency artifact, arguing that model cards describe the trained artifact while route receipts should describe the execution path that produced a specific answer.

That is very close to the direction explored with VALO / VAIG governance receipts.

The next competitive advantage may not be the smartest model.

It may be the provider that can prove exactly what happened during execution.

---

## VALO interpretation

This connects directly to the earlier inference-identity note:

```text
Model identity is not enough.
Execution identity is the purchased unit.
```

A serious enterprise execution receipt should bind:

```text
Inference Identity
+ Route Identity
+ Governance Policy Identity
+ Calibration Identity
+ Tool Identity
+ Receipt Signature
```

The result is not just observability.

It is procurement-grade proof of execution quality.

---

## Compression

```text
Model cards describe capability.
Route receipts describe what actually happened.
SLAs govern service availability.
ELAs govern execution quality.
```

VALO / VAIG can be positioned as the governance and proof layer for this shift.
