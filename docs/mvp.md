# VALO Twin MVP

This MVP is not a LinkedIn content generator.

It is a governed digital twin prototype with content generation as one visible workflow.

Correct product name:

```text
valo-twin-content-engine
```

## Product thesis

A digital twin should not only remember a person, company or agent.

It should understand context, map capabilities, suggest actions and route those actions through governance before anything is published, sent or executed.

## MVP scope

The first MVP should prove this flow:

```text
Import material
  |
  v
Build Twin Profile
  |
  v
Find Skills + Evidence
  |
  v
Profile DNA
  |
  v
Generate content / message / action suggestion
  |
  v
Approval Queue
  |
  v
VAIG / RETH-style review
  |
  v
Governance Receipt
```

## What to build first

### 1. Manual import

Avoid making the MVP dependent on LinkedIn API access.

Support:

- pasted text
- CV upload
- Markdown files
- PDF/text documents
- GitHub repo summary
- LinkedIn post history pasted manually
- website text

### 2. Twin Profile

A profile can represent:

- person
- company
- agent

The system should not assume every profile is a human user.

### 3. Find Skills

Extract:

- claimed skills
- inferred skills
- evidenced skills
- weakly evidenced skills
- missing skills
- outdated skills

Each skill should link to evidence.

### 4. Profile DNA

Extract:

- themes
- tone
- writing style
- recurring concepts
- strongest claims
- weak claims
- best hooks
- positioning
- audience

### 5. Content Engine

Generate suggestions for:

- LinkedIn post
- LinkedIn comment
- direct message
- short email
- website paragraph
- investor update
- sales follow-up

Do not autopublish in the MVP.

### 6. Approval Queue

Every suggestion must enter a queue before action.

Possible decisions:

- approve
- edit
- pause
- reject
- needs evidence
- needs human review

### 7. Governance Receipt

Every suggestion should produce a receipt:

- profile id
- source material ids
- generated output hash
- evidence references
- risk flags
- approval decision
- reviewer
- timestamp
- final status

## Database model

Minimum entities:

```text
twin_profiles
  id
  type                 # person | company | agent
  name
  summary
  profile_dna_json
  created_at
  updated_at

source_documents
  id
  twin_profile_id
  source_type          # cv | github | linkedin | website | pdf | markdown | manual
  title
  content
  metadata_json
  consent_scope_id
  created_at

skills
  id
  twin_profile_id
  name
  category
  claim_type           # claimed | inferred | evidenced | admissible
  confidence
  recency_score
  created_at

skill_evidence
  id
  skill_id
  source_document_id
  excerpt
  evidence_type        # text | credential | code | project | outcome | receipt
  confidence
  verified_state       # unverified | weak | strong | external
  created_at

skill_gaps
  id
  twin_profile_id
  target_context       # role | project | tender | customer | roadmap
  missing_skill
  severity
  recommendation
  created_at

content_suggestions
  id
  twin_profile_id
  channel              # linkedin | email | dm | website | investor | sales
  content
  score
  risk_level
  evidence_status
  status               # draft | queued | approved | rejected | published
  created_at

approval_queue
  id
  twin_profile_id
  suggestion_id
  requested_action
  status               # pending | approved | rejected | needs_evidence | paused
  reviewer
  decision_reason
  created_at
  decided_at

governance_receipts
  id
  twin_profile_id
  action_type
  action_hash
  evidence_json
  risk_flags_json
  decision
  reviewer
  receipt_hash
  created_at

connectors
  id
  name
  connector_type       # manual | github | linkedin | drive | gmail | calendar | api
  status
  config_json
  created_at

consent_scopes
  id
  twin_profile_id
  connector_id
  read_allowed
  store_allowed
  infer_allowed
  reuse_allowed
  share_allowed
  action_allowed
  expires_at
  created_at
```

## ER model

```text
                          twin_profiles
                                |
      -----------------------------------------------------
      |             |              |           |           |
source_documents   skills   content_suggestions  connectors consent_scopes
      |             |              |                       |
      |        skill_evidence      |                       |
      |             |              |                       |
      |        skill_gaps     approval_queue               |
      |                            |                       |
      ---------------------- governance_receipts -----------
```

## API routes

Minimum API:

```text
POST   /import/manual
POST   /import/github-summary
GET    /profiles/:id
POST   /profiles/:id/analyze
GET    /profiles/:id/skills
GET    /profiles/:id/skill-gaps
POST   /profiles/:id/generate
GET    /approval-queue
POST   /approval-queue/:id/decision
GET    /receipts/:id
```

## Frontend screens

First UI should have only five screens:

1. Import
2. Twin Profile
3. Skills + Evidence
4. Suggestions
5. Approval + Receipt

Avoid dashboards that show too much too early.

## MVP demo script

Best first demo:

1. Upload CV, GitHub summary and 10 LinkedIn posts.
2. System builds Twin Profile.
3. System extracts skills and links each to evidence.
4. System finds one weakly evidenced claim.
5. System generates a LinkedIn post.
6. VAIG/RETH-style review flags unsupported claim.
7. User edits or adds evidence.
8. System approves.
9. Receipt is created.

This demonstrates the core distinction:

```text
AI can generate.
VALO decides whether the generated action is admissible.
```

## What not to build in MVP

Do not build first:

- full LinkedIn OAuth
- automatic posting
- multi-company marketplace
- full agent org chart
- complex scraping system
- CRM/accounting integrations
- complete data vault
- autonomous execution

These come later.

## Technical stack

Recommended simple stack:

- Next.js / React frontend
- FastAPI or Hono backend
- PostgreSQL
- pgvector or Qdrant
- Redis for queue/cache
- MinIO for files
- local Markdown export
- optional Ollama/local model support
- LiteLLM for model abstraction

## Product category

This should be positioned as:

```text
Governed Digital Twin
```

Not:

```text
LinkedIn generator
```

The LinkedIn workflow is only the first visible use case.

The real product is:

```text
Digital Twin -> Find Skills -> Suggest Action -> Governance -> Receipt
```
