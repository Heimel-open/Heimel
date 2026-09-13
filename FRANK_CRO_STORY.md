# From Compliance Officer to Governance Architect

**Frank Garneng's Journey: Building Admissibility Enforcement for Enterprise AI**

---

## The Problem Frank Solved

Frank spent 15 years in GRC (Governance, Risk, Compliance). He built frameworks. He wrote policies. He got audited.

Then AI happened.

The first problem was obvious: **"How do we ensure our AI systems follow our policies?"**

Credo AI, OneTrust, Holistic AI — all solved this. Policy → Documentation → Audit Trail.

But after Frank deployed their solutions, he found a second problem nobody was solving:

**"How do we ensure our autonomous AI systems make legitimate decisions in real-time?"**

That's different from policy compliance. A decision can be *policy-compliant* but *epistemically incoherent*. An agent can have permission to act but no legitimate basis for deciding to act.

Frank's insight: **Compliance doesn't equal control.**

---

## Why Frank's Background Matters

**Traditional GRC path:**
- Build policy framework
- Document adherence
- Audit compliance
- Hope it worked

**New reality:**
- Build policy framework
- **Enforce at runtime**
- Decide autonomously in real-time
- Prove legitimacy post-facto

Nobody from the compliance world was building the runtime enforcement layer. Everyone from the security world was building tool firewalls (AEGIS) or policy gates (TrigGuard), but nobody was building **admissibility enforcement** — the layer that says "is this decision legitimate enough to execute?"

Frank recognized the gap because he lived in compliance. He knew policy wasn't enough. He knew organizations needed to *prove* governance worked, not just document it.

---

## The Realization

Frank was at a board meeting. A fintech client had deployed an autonomous trading agent. The agent made a $500M position in commodities. The reasoning was internally coherent (from the agent's perspective), but externally it violated every principle the board had set.

The board asked: "Where was the control?"

Frank realized: "Compliance said yes. Policy said yes. But nobody asked: should the agent have made that decision *in the first place*?"

That's not a policy question. That's an admissibility question.

**Policy answers:** "Are we allowed to do this?"  
**Admissibility answers:** "Should we be doing this?"

---

## Building VAIG

Frank partnered with researchers who had been working on formal governance models. Together they built VAIG:

- **Evidence gating** — does the agent have legitimate basis for deciding?
- **Admissibility scoring** — is the decision epistemologically sound?
- **Safe Mode** — what happens when a decision fails admissibility?
- **RRP (Refusal Resolution Protocol)** — how does refusal become governable?
- **Receipt/WORM** — cryptographic proof of decision legitimacy

The key innovation: **admissibility as a runtime enforcement layer, not post-hoc audit.**

---

## What Makes Frank Different

**Traditional CISO approach:**
"We need a firewall for AI. We need to block dangerous actions."

**Frank's approach:**
"We need a governance layer. We need to prove decisions are legitimate before they execute."

Frank brought three things security people didn't have:

1. **Regulatory language** — admissibility isn't just "safe," it's defensible to regulators
2. **Board-level understanding** — can articulate why this matters to a CFO (ROI, not security)
3. **Organizational authority** — as a CRO, Frank can mandate this gets adopted

---

## The Three Positions

### Layer 3: Policy (Frank's original domain)
> "What are we allowed to do?"
> 
> Answered by: Credo AI, OneTrust, compliance frameworks

### Layer 1: Admissibility (Frank's new domain)
> "Should we be doing this right now?"
> 
> Answered by: VAIG + Frank's governance authority

### Layer 2: Observability (DevOps/Security domain)
> "What actually happened?"
> 
> Answered by: AI Trust OS, Datadog, observability platforms

**Together:** Verifiable governance. Board can sleep.

---

## Frank's Pitch to the Board

> We've solved compliance documentation. We pass audits. But we can't control execution in real-time.
>
> VAIG changes that. Every autonomous decision goes through admissibility gating. We prove it was legitimate *before* it had consequences.
>
> Cost: $500k/year.  
> Benefit: Prevent one bad $1M+ decision in your first year.  
> Risk prevented: Regulatory fine for inability to prove control.
>
> That's why I'm personally signing off on this layer.

---

## What Frank Gets Wrong (And Learns)

Frank initially thought admissibility was about *correctness*. "Let's make sure the AI makes the right decision."

The researchers corrected him: "No. We're not deciding rightness. We're deciding admissibility. Is there enough evidence for the decision to be made at all? By whom? Under what constraints?"

Frank realized admissibility is **not** about AI safety. It's about **organizational legitimacy**.

It's not: "Will this decision be correct?"  
It's: "Does this organization have the authority and evidence to let an agent make this decision?"

That subtle shift is what makes VAIG work across different industries, different domains, different regulations.

---

## The Market Frank Is Building

**Year 1:** "Autonomous AI needs governance"
- 5 pilot customers
- $500k ARR
- VAIG recognized as "missing layer"

**Year 2:** "Governance must be verifiable"
- 20 enterprise customers
- $5M ARR
- VAIG becomes table stakes for regulated autonomous AI

**Year 3:** "Admissibility is a standard"
- Frank contributes to IETF standard
- VAIG is bundled with agent platforms (Claude API, Arcade, LangGraph)
- $50M+ market leader

---

## The Interview Frank Gives to VCs (2026-09)

**Q: Why VAIG instead of AEGIS?**

A: AEGIS answers "is this tool call dangerous?" We answer "is this decision legitimate?" Different questions. AEGIS prevents bad actions. We prevent bad decisions. Complementary, not competitive.

**Q: Why you instead of another founder?**

A: I come from compliance. Every other founder in this space comes from security. I know what regulators care about: provable governance. I can speak both to CROs and to security teams. That's rare.

**Q: What's the biggest risk?**

A: The market doesn't realize it needs this yet. But give it one incident — one autonomous AI making a bad decision that should have been caught — and suddenly admissibility governance becomes critical.

**Q: What's the 3-year vision?**

A: VAIG becomes the governance layer every autonomous AI system needs. Like CORS and CSRF protection became standard, VAIG + AEGIS become standard. We own the admissibility piece.

---

## Why This Story Matters

**For investors:**
Frank gives credibility. He's not a security researcher. He's a governance person building the governance layer. That's defensible.

**For customers:**
Frank speaks their language. Board members trust CROs. When Frank says "this is table stakes," they listen.

**For the market:**
Frank positions VAIG as governance innovation, not security tool. That's a different sales cycle, different customer base, different urgency.

**For VALO:**
Frank as CRO validates that this is about organizational legitimacy, not technical cleverness. That's the story that wins the market.

---

## The Personal Arc

Frank spent 15 years building compliance. He realized compliance wasn't enough.

Now he's building the enforcement layer that makes compliance real.

**That's why he's perfect for this role. And why this market is ready.**
