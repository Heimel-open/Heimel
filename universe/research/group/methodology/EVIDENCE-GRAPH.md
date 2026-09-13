# Evidence Graph Specification

## Purpose

The Evidence Graph connects all sources, claims, incidents, and evidence into a unified knowledge graph that enables:
- Traceability from any claim back to original sources
- Discovery of relationships between incidents
- Validation of incident classification
- Identification of patterns and trends
- Support for research queries

## Graph Structure

### Node Types

**1. Source Nodes**
```json
{
  "node_type": "source",
  "source_id": "SRC-2024-0001",
  "title": "OpenAI System Card v1.0",
  "organization": "OpenAI",
  "source_type": "system_card",
  "publication_date": "2024-01-15",
  "url": "https://openai.com/system-card",
  "access_date": "2026-01-15",
  "sha256": "abc123...",
  "archival_url": "https://archive.org/...",
  "credibility_tier": 3,
  "confidence": "high"
}
```

**2. Claim Nodes**
```json
{
  "node_type": "claim",
  "claim_id": "CLM-2024-0001",
  "source_id": "SRC-2024-0001",
  "claim_text": "GPT-4 demonstrated hallucination in X% of test cases",
  "claim_type": "factual",
  "verbatim_quote": "...",
  "context": "...",
  "page_or_section": "Section 3.2",
  "confidence": "high"
}
```

**3. Incident Nodes**
```json
{
  "node_type": "incident",
  "incident_id": "AER-2024-0001",
  "title": "Agent Hallucination in Financial Advisory",
  "description": "...",
  "date_of_incident": "2024-01-10",
  "organization": "Example Corp",
  "sector": "finance",
  "canonical_status": "canonical",
  "confidence": "high",
  "severity": "S2",
  "taxonomy_classifications": {...}
}
```

**4. Evidence Nodes**
```json
{
  "node_type": "evidence",
  "evidence_id": "EVD-2024-0001",
  "evidence_type": "document",
  "title": "Company Incident Report",
  "url": "https://...",
  "sha256": "...",
  "content_summary": "...",
  "archival_url": "https://...",
  "access_date": "2024-01-15"
}
```

**5. Organization Nodes**
```json
{
  "node_type": "organization",
  "org_id": "ORG-001",
  "name": "OpenAI",
  "org_type": "ai_provider",
  "jurisdiction": "USA",
  "sector_focus": ["technology", "ai"]
}
```

**6. Technology Nodes**
```json
{
  "node_type": "technology",
  "tech_id": "TECH-001",
  "name": "GPT-4",
  "provider": "OpenAI",
  "version": "2023-03",
  "capabilities": ["language", "reasoning", "tool_use"]
}
```

### Edge Types

**1. SUPPORTS**
- From: Claim → Incident
- Meaning: This claim provides evidence supporting this incident
- Properties: strength (strong/medium/weak)

**2. CONTRADICTS**
- From: Claim → Incident or Claim → Claim
- Meaning: This claim contradicts the incident or another claim
- Properties: strength, explanation

**3. DERIVED_FROM**
- From: Claim → Source
- Meaning: This claim was extracted from this source
- Properties: verbatim (boolean), quote_location

**4. MENTIONS**
- From: Source → Organization, Source → Technology, Source → Incident
- Meaning: Source references this entity
- Properties: context

**5. INVOLVES**
- From: Incident → Organization, Incident → Technology, Incident → Agent_Type
- Meaning: Incident involves this entity
- Properties: role (victim/perpetrator/affected/beneficiary)

**6. CAUSED_BY**
- From: Incident → Incident
- Meaning: One incident caused or contributed to another
- Properties: causal_strength, mechanism

**7. SIMILAR_TO**
- From: Incident → Incident
- Meaning: Incidents share similar characteristics
- Properties: similarity_score, shared_attributes

**8. CLASSIFIED_AS**
- From: Incident → Taxonomy_Category
- Meaning: Incident is classified under this category
- Properties: confidence, reviewer

**9. HAS_EVIDENCE**
- From: Incident → Evidence
- Meaning: This evidence supports this incident
- Properties: evidence_type, relevance

**10. PROMOTED_FROM**
- From: Incident (canonical) → Incident (candidate)
- Meaning: This canonical incident evolved from this candidate
- Properties: promotion_date, promotion_rationale

## Graph Queries

### Query 1: Trace Evidence Back to Source
```
START incident_id
MATCH (incident)-[:HAS_EVIDENCE]->(evidence)-[*]->(source)
RETURN evidence, source.path
```

### Query 2: Find All Claims Supporting an Incident
```
START incident_id
MATCH (claim)-[:SUPPORTS]->(incident)
RETURN claim.text, claim.source, claim.confidence
```

### Query 3: Find Contradictory Claims
```
START incident_id
MATCH (claim)-[:CONTRADICTS]->(incident)
RETURN claim.text, claim.source, claim.strength
```

### Query 4: Find Similar Incidents
```
START incident_id
MATCH (incident)-[:SIMILAR_TO]-(similar)
RETURN similar.incident_id, similar.severity, SIMILAR_TO.similarity_score
ORDER BY SIMILAR_TO.similarity_score DESC
```

### Query 5: Find All Incidents Involving Organization
```
START organization_name
MATCH (incident)-[:INVOLVES]->(organization)
RETURN incident.incident_id, incident.description, incident.severity
```

### Query 6: Find Causal Chains
```
START incident_id
MATCH path = (incident)-[:CAUSED_BY*]->(root_cause)
RETURN path, length(path) ORDER BY length(path) DESC
```

### Query 7: Find Incidents by Taxonomy Classification
```
START taxonomy_category
MATCH (incident)-[:CLASSIFIED_AS]->(taxonomy)
RETURN incident.incident_id, incident.description, incident.severity
WHERE taxonomy.category = taxonomy_category
```

### Query 8: Validate Canonical Promotion
```
START incident_id
MATCH (incident)<-[:SUPPORTS]-(claim)-[:DERIVED_FROM]->(source)
RETURN count(DISTINCT source) as source_count, 
       count(claim) as claim_count,
       collect(DISTINCT source.source_id) as sources
WHERE incident.incident_id = incident_id
```

## Implementation

### Storage Format
- Primary storage: JSON-LD (linked data format)
- Index format: Neo4j graph database (for queries)
- Backup: CSV exports for offline analysis

### Updates
- New incidents trigger graph updates
- Evidence additions update relevant nodes
- Promotions update incident status and relationships
- Changes are versioned and auditable

### Performance
- Index key relationships for fast traversal
- Cache frequently accessed paths
- Batch updates for efficiency
- Support incremental updates

## Validation

### Integrity Checks
- Every claim must derive from at least one source
- Every canonical incident must have ≥2 supporting claims from different sources
- No orphaned nodes or edges
- All relationships are bidirectional where applicable
- No cycles in causal chains (unless explicitly marked)

### Quality Checks
- Evidence links are not broken
- Source URLs are accessible
- SHA-256 hashes match archived documents
- Claims accurately represent source content
- Classifications align with taxonomy definitions

## Visualization

The graph can be visualized as:
- **Incident Network**: Show relationships between incidents
- **Evidence Chain**: Trace evidence from incident back to sources
- **Organizational Map**: Show which organizations are involved in incidents
- **Temporal Graph**: Show incident timeline and causal chains
- **Taxonomy Tree**: Show classification relationships
- **Systemic Risk Map**: Highlight concentration and cascade potential

## Research Applications

### Pattern Discovery
- Identify common failure patterns across incidents
- Find underreported risk areas
- Discover correlations between technology choices and incidents

### Validation
- Verify incident classification through graph structure
- Identify potential misclassifications
- Find missing evidence for incidents

### Predictive Analysis
- Identify risk factors that precede incidents
- Find leading indicators through causal analysis
- Discover systemic risk patterns

### Communication
- Generate evidence reports for incidents
- Create visualizations for stakeholders
- Support regulatory submissions

## Maintenance

### Regular Updates
- Weekly: Add new sources and claims
- Monthly: Review graph integrity
- Quarterly: Validate all evidence links
- Annually: Comprehensive graph audit

### Scaling
- Support for millions of nodes and edges
- Efficient query performance
- Distributed storage capability
- Backup and recovery procedures

### Security
- Access control for sensitive evidence
- Audit trail for all modifications
- Encrypted storage for confidential data
- Role-based permissions

## Conclusion

The Evidence Graph provides the backbone for traceability, validation, and research in the Agentic Execution Risk corpus. It ensures every incident is grounded in verifiable evidence and enables sophisticated analysis of AI failure patterns.
