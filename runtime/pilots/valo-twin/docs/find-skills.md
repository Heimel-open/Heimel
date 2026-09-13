# Find Skills

Find Skills is a first-class VALO Twin module.

It turns the digital twin from a memory system into a capability system.

The module answers four questions:

1. What skills does this person, company or agent actually have?
2. What evidence supports those skills?
3. What skills are missing for a goal, project, tender or customer need?
4. Who or what can fill the gap?

## Purpose

Find Skills maps capability, evidence and gaps across people, companies, agents and tools.

It should support:

- personal skill mapping
- company capability mapping
- project team composition
- consultant matching
- agent matching
- tender readiness
- sales qualification
- internal mobility
- AI-generated CV and LinkedIn updates
- evidence-backed positioning

## Sources

Skills can be inferred from:

- CV and LinkedIn profile
- GitHub repositories, commits, issues and pull requests
- documents, proposals, reports and presentations
- email and meeting history
- calendar patterns and project involvement
- articles, posts, podcasts and talks
- certifications, courses and credentials
- invoices, customer cases and delivered work
- agent execution history and governance receipts

## Skill evidence model

A skill should never be only a label.

Every skill should carry evidence.

```text
Skill
  |
  +--> Evidence
  |      +--> source
  |      +--> timestamp
  |      +--> excerpt / artifact
  |      +--> confidence
  |      +--> verification state
  |
  +--> Context
  |      +--> project
  |      +--> domain
  |      +--> tool / framework
  |      +--> recency
  |
  +--> Governance
         +--> consent scope
         +--> shareability
         +--> admissibility state
```

A skill is stronger when it is recent, repeated, externally evidenced and connected to real outcomes.

## Skill graph

The graph should connect:

```text
Person / Company / Agent
  |
  +--> Skill
  |      +--> Evidence
  |      +--> Project
  |      +--> Outcome
  |      +--> Tool
  |      +--> Domain
  |
  +--> Skill Gap
         +--> Requirement
         +--> Recommended person
         +--> Recommended agent
         +--> Recommended training
```

## Skill gap detection

The twin should compare current capabilities against a target.

Targets can be:

- job role
- project requirement
- tender requirement
- customer need
- startup roadmap
- compliance framework
- agent task
- market opportunity

Output:

- existing skills
- missing skills
- weakly evidenced skills
- outdated skills
- recommended training
- recommended collaborators
- recommended agents
- evidence needed before claiming the skill publicly

## Routing layer

Find Skills connects directly to the Skill Router / SOL Routing Layer.

The system should not only ask which model can solve a task.

It should ask which skill can solve it.

A skill can be:

- a human
- an agent
- a local model
- a specialist model
- a workflow
- a tool
- an API
- a verified VALO module

Routing question:

Which skill can solve this task with the best balance of cost, quality, latency, privacy and governance risk?

## Governance rule

The twin may infer a skill internally.

It must not publicly claim a skill unless the evidence is admissible.

VAIG/RETH should check whether a skill claim is supported before it is used in:

- CV
- proposal
- LinkedIn post
- tender response
- customer pitch
- agent marketplace profile

## MVP

First MVP should be simple:

1. Upload CV, GitHub repo summary, LinkedIn text and documents.
2. Extract candidate skills.
3. Link each skill to evidence.
4. Score confidence and recency.
5. Show missing evidence.
6. Generate a skill profile.
7. Run VAIG/RETH before any external claim.

The demo should show the difference between:

- claimed skill
- inferred skill
- evidenced skill
- admissible public claim

That distinction is the product value.
