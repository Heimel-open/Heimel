# Methodology: Building the Canonical Incident Corpus

## 1. Data Collection Strategy

### 1.1 Primary Source Hierarchy

We prioritize authoritative primary sources to ensure evidence quality:

**Tier 1: Government Regulators & Investigators**
- NTSB (aviation safety)
- NHTSA (vehicle safety)
- CISA (cybersecurity)
- NIST (standards & best practices)
- FDA (medical devices)
- FAA (unmanned aircraft)
- DOJ (enforcement)
- FTC (consumer protection)
- SEC (securities)
- CFPB (financial services)
- EU AI Office
- ENISA (EU cybersecurity)
- National regulatory bodies

**Tier 2: International Standards Bodies**
- OECD AI Incidents Monitor
- MITRE ATLAS
- MITRE ATT&CK
- ISO working groups
- IEEE standards committees

**Tier 3: Frontier AI Companies**
- OpenAI System Cards
- Anthropic System Cards
- Google DeepMind Safety Reports
- Microsoft AI Security Reports
- Meta AI Safety Publications
- GitHub Security Advisories

**Tier 4: Industry Incident Databases**
- AI Incident Database (aiaid.org)
- AIDA (AI Deployment Assessment)
- Partnership on AI incident tracking
- Industry-specific incident databases

**Tier 5: Academic Research**
- Stanford AI Index
- AI Now Institute
- Peer-reviewed journals (Nature, Science, JAIR, etc.)
- Conference proceedings (NeurIPS, ICML, AAAI, etc.)
- arXiv papers

**Tier 6: Credible Journalism & Documentation**
- Investigative journalism (only for incident discovery, must verify with primary sources)
- Company blog posts (only when no better source available)
- Community reports (with verification)

### 1.2 Collection Process

```
SOURCE_DISCOVERY → SOURCE_VALIDATION → INCIDENT_EXTRACTION → 
EVIDENCE_PRESERVATION → CLAIM_EXTRACTION → CLASSIFICATION → 
CANONICAL_PROMOTION_REVIEW → CANONICAL_INCIDENT
```

**Source Discovery**
- Identify potential sources via systematic search
- Track source URLs, publication dates, authorship
- Verify source credibility and authority

**Source Validation**
- Confirm source is authoritative (government, company, peer-reviewed)
- Verify publication date and currency
- Check for conflicts of interest
- Ensure source is citable and accessible

**Incident Extraction**
- Extract all incidents mentioned in source
- Record exact quotes and context
- Preserve original numbering/referencing
- Note any uncertainty or caveats in source

**Evidence Preservation**
- Capture SHA-256 hash of source (where possible)
- Archive source in wayback machine or local archive
- Download and store PDF copies
- Record access date
- Preserve version information

**Claim Extraction**
- Break down incidents into discrete claims
- Each claim must be independently verifiable
- Link claims to specific source passages
- Identify supporting evidence for each claim

**Classification**
- Apply failure taxonomy (see taxonomy.yaml)
- Classify by sector, technology, autonomy level
- Assess severity and systemic risk
- Identify contributing factors

**Canonical Promotion Review**
Multi-stage review:
1. Automated deduplication check
2. Cross-reference with other sources
3. Verify claims are independently sourced
4. Check classification consistency
5. Assess evidence quality
6. Review by second analyst

**Canonical Incident**
- Assign canonical ID (AER-YYYY-XXXX)
- Create structured incident record (schema.yaml)
- Link to all supporting evidence
- Document promotion rationale
- Mark as canonical in registry

### 1.3 Canonical Promotion Criteria

An incident achieves canonical status ONLY when ALL of the following are met:

1. **Multiple Primary Sources**: At least 2 independent credible sources report the incident
2. **Primary Source Availability**: Original source documents are accessible and archived
3. **Claim Verification**: All major claims are verified against primary sources
4. **Duplicate Check**: No duplicate incidents exist (or duplicates are properly merged)
5. **Timeline Verified**: Incident timeline (discovery, occurrence, reporting) is consistent
6. **Evidence Preserved**: SHA-256 hashes or archival copies exist for key sources
7. **Classification Reviewed**: Taxonomy classification has been reviewed by second analyst
8. **No Contradictory Evidence**: No credible sources directly contradict core claims

## 2. Data Quality Standards

### 2.1 Evidence Quality Tiers

**High Quality**
- Primary source (government report, company disclosure)
- Peer-reviewed research
- Multiple independent sources agree
- Direct quotes and documentation available
- Archival evidence preserved

**Medium Quality**
- Primary source but limited documentation
- Single credible source
- Some claims unverifiable
- Missing context
- Potential conflicts of interest

**Low Quality**
- Secondary sources only
- Anonymous reports
- Unverified claims
- Missing key details
- Speculative content

### 2.2 Verification Requirements

For each incident, we must verify:
- **What happened**: Specific actions taken by AI system
- **When it happened**: Discovery date, occurrence date, reporting date
- **Who was affected**: Organizations, individuals, systems
- **What was the impact**: Financial, operational, safety, reputational
- **What caused it**: Root cause analysis
- **What was the response**: Remediation, regulatory action, system changes

### 2.3 Confidence Scoring

Each incident receives a confidence score:

**High Confidence (≥80%)**
- Multiple primary sources
- All claims verified
- Strong documentary evidence
- Consistent reporting

**Medium Confidence (50-79%)**
- One or two primary sources
- Most claims verified
- Some gaps in evidence
- Minor inconsistencies resolved

**Low Confidence (<50%)**
- Limited primary sources
- Significant unverifiable claims
- Major gaps in evidence
- Inconsistent reporting

## 3. Cross-Source Validation

### 3.1 Source Triangulation

When multiple sources report the same incident:
- Compare timelines for consistency
- Identify which source is primary vs secondary
- Look for independent corroboration
- Note any discrepancies
- Resolve conflicts through additional research

### 3.2 Contradiction Handling

If sources contradict:
- Document all positions
- Assess credibility of each source
- Look for additional sources
- Mark incident as "under investigation"
- Do NOT promote to canonical until resolved

### 3.3 Deduplication Protocol

When multiple sources report similar incidents:
- Check if incidents are truly identical or related
- If identical: merge into single canonical incident with multiple sources
- If related: create separate incidents with cross-references
- Preserve all unique information from each source
- Document deduplication rationale

## 4. Temporal Validation

### 4.1 Timeline Construction

For each incident, construct timeline:
- **Incident Date**: When failure actually occurred
- **Discovery Date**: When incident was first detected
- **Reporting Date**: When incident was publicly reported
- **Investigation Date**: When investigation began
- **Resolution Date**: When incident was resolved
- **Regulatory Action Date**: When regulators took action

### 4.2 Timeline Consistency Check

Verify:
- Discovery date ≥ incident date (can't discover before it happened)
- Reporting date ≥ discovery date (can't report before discovery)
- Resolution date ≥ investigation date (can't resolve before investigating)
- All dates are internally consistent with source documents

## 5. Classification Validation

### 5.1 Taxonomy Application

Apply failure taxonomy systematically:
- Primary failure category
- Secondary failure categories
- Severity level
- Autonomy level
- Propagation pattern
- Systemic risk indicators

### 5.2 Inter-Rater Reliability

For canonical promotion:
- Two independent analysts classify incident
- Compare classifications
- Resolve disagreements through discussion
- Document classification rationale
- Maintain classification consistency

## 6. Systemic Risk Assessment

### 6.1 Systemic Risk Indicators

Classify systemic risk based on:

**None**: Isolated incident, no broader implications

**Low**: Could affect similar systems in same organization

**Medium**: Could affect similar systems across industry

**High**: Could affect multiple industries or create cascading failures

**Critical**: Could cause systemic financial, safety, or societal harm

### 6.2 Systemic Risk Factors

Evaluate:
- How many organizations could be affected?
- How concentrated is the underlying technology?
- How dependent are critical systems?
- What are the potential cascading effects?
- Is there potential for correlated failures?
- Could this trigger broader market/societal impact?

## 7. Financial Impact Estimation

### 7.1 Direct Costs
- Immediate financial loss
- Remediation costs
- Regulatory fines
- Legal settlement costs
- Customer compensation
- Incident response costs

### 7.2 Indirect Costs
- Reputational damage
- Customer churn
- Increased insurance premiums
- Compliance costs
- Opportunity costs
- Long-term brand value impact

### 7.3 Estimation Methodology

When exact figures are unavailable:
- Use reported ranges (note range in record)
- Cite analyst estimates (with source)
- Use comparable incident data
- Note uncertainty explicitly
- Provide low/medium/high estimates

## 8. Documentation Standards

### 8.1 Incident Record Completeness

Every canonical incident must have:
- All required schema fields populated
- At least 2 primary source citations
- SHA-256 hash or archival link for primary sources
- Complete timeline
- Taxonomy classification
- Confidence score
- Systemic risk assessment
- Financial impact estimate
- Promotion rationale

### 8.2 Evidence Chain

Maintain clear evidence chain:
- Source → Claims → Incident
- Each claim linked to specific source passage
- Source archival evidence preserved
- Cross-references to related incidents
- Supporting documentation stored

### 8.3 Audit Trail

Maintain audit trail for each incident:
- Date incident was added to corpus
- Date canonical promotion was requested
- Dates of all reviews
- Reviewer identities
- Promotion decision rationale
- Any changes or updates made

## 9. Ongoing Maintenance

### 9.1 Continuous Collection

- Regular monitoring of primary sources
- Automated alerts for new incidents
- Systematic literature reviews
- Industry database updates
- Regulatory action tracking

### 9.2 Periodic Review

- Quarterly review of candidate incidents
- Annual comprehensive taxonomy review
- Biennial methodology review
- Update classifications as new evidence emerges
- Re-assess confidence scores

### 9.3 Version Control

- Track all changes to canonical incidents
- Document why changes were made
- Preserve historical versions
- Maintain change log
- Notify users of significant updates

## 10. Research Applications

This methodology enables:

**Empirical Research**
- Statistical analysis of failure patterns
- Risk factor identification
- Trend analysis over time
- Cross-sector comparison
- Technology-specific analysis

**Regulatory Analysis**
- Evidence-based policy recommendations
- Regulatory impact assessment
- Compliance gap analysis
- Enforcement effectiveness evaluation

**Industry Benchmarking**
- Failure rate comparison
- Best practice identification
- Risk severity benchmarking
- Response effectiveness analysis

**Predictive Modeling**
- Incident forecasting
- Risk probability estimation
- Systemic risk early warning
- Intervention effectiveness prediction

## 11. Limitations and Caveats

### 11.1 Known Limitations

- Publication bias: not all incidents are publicly reported
- Reporting delays: incidents may be reported long after occurrence
- Incomplete information: some details may never be publicly available
- Definition variance: different sources may define "incident" differently
- Self-reporting bias: companies may underreport or spin incidents

### 11.2 Appropriate Use

This corpus is appropriate for:
- Academic research
- Regulatory analysis
- Industry benchmarking
- Risk assessment
- Policy development

This corpus is NOT appropriate for:
- Individual legal cases
- Specific compliance determinations
- Real-time operational decisions
- Marketing claims about system safety

## 12. Methodology Evolution

This methodology will evolve as:
- New incident sources emerge
- Evidence collection techniques improve
- Taxonomy classifications are refined
- Research applications reveal gaps
- Regulatory requirements change

All methodology changes will be:
- Documented in version history
- Applied to future incidents only
- Not retroactively applied to canonical incidents
- Reviewed and validated before adoption
