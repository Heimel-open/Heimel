# Unlimited-OCR and Agent Use

Status: Technical signal note
Date: 2026-06-24
Scope: Agentic document workflows, RAG, evidence ingestion, VALO/VAIG architecture

## Core Assessment

Unlimited-OCR is relevant for agent use.

But not as agent intelligence.

As document perception.

The important shift is not that OCR becomes smarter in the abstract. The important shift is architectural: long documents can be parsed without the usual brittle chain of page-by-page OCR, manual stitching, chunk reconstruction, and then RAG ingestion.

If the model can keep the document visible while carrying only a sliding working state of generated text, long-document parsing becomes less of a reconstruction job and more of a streaming perception problem.

That matters for agents.

## Where It Fits

Correct placement:

Document -> OCR / vision parser -> provenance-bound evidence chunks -> agent reasoning -> VALO Gate -> action or halt

Unlimited-OCR belongs in the perception layer.

It does not belong in the authority layer.

It helps an agent see documents.

It does not give the agent permission to act.

## Useful Agent Domains

Strong fit:

- due diligence
- contract review
- policy review
- legal/compliance intake
- technical manuals
- RFP and tender analysis
- PDF-heavy data rooms
- board packs
- insurance claims
- procurement documents
- regulatory filings
- research paper ingestion

In these domains, the agent's first failure mode is often not reasoning. It is bad document perception.

If the input is broken, the reasoning is already contaminated.

## VALO Interpretation

For VALO, this is an evidence ingestion component.

It can strengthen:

- EvidenceCondition
- ClaimSubstantiation
- SourceTraceability
- DocumentGrounding
- RAG quality
- audit preparation

It does not satisfy:

- AuthorityCondition
- HumanSignoff
- PolicyApproval
- ExecutionPermission
- final admissibility

OCR can support a decision.

OCR cannot authorize a decision.

## Required Controls

For agentic use, every extracted fragment should carry provenance:

- original file hash
- page number
- region or bounding box
- extraction confidence
- model name and version
- timestamp
- chunk id
- source image reference
- downstream citation id

Low-confidence extraction must route to review.

Tables, equations, handwriting, scanned pages, diagrams, stamps, signatures, and footnotes should be treated as higher-risk regions.

## Main Risk

The danger is not old OCR misreading characters.

The danger is generative OCR producing plausible text that was never actually in the document.

That is worse than ordinary OCR error because it looks fluent.

So the rule is simple:

OCR is sensorics, not truth.

A document parser can say what it believes it saw.

A governed system must still prove where it saw it.

## VALO Rule

No agent action should be allowed from parsed document text alone.

Required chain:

Parsed text -> cited source region -> evidence check -> policy check -> authority check -> receipt -> action

If any link is missing, the system should defer, step up, or halt.

## Conclusion

Unlimited-OCR is a serious signal for agentic document workflows.

It may reduce one of the biggest practical bottlenecks in enterprise agents: long, messy document ingestion.

But it does not solve agent safety.

It moves the boundary.

The agent can read more.

Therefore the governance layer becomes more important, not less.

For VALO, the correct framing is:

Document perception is improving.

Execution control is still missing.
