```mermaid
stateDiagram-v2
    direction LR

    [*] --> EMITTED : VAIG produces refusal

    state EMITTED {
        [*] --> enriched
    }

    EMITTED --> ENRICHED : RRP Enrichment Service

    state ENRICHED {
        [*] --> routed
        note right of ENRICHED
            Uncertainty Inventory populated
            Model integrity assessed
            Pattern indicators flagged
        end note
    }

    ENRICHED --> ROUTED : RRP Router
    ENRICHED --> RESOLVED : Auto-resolved (advisory)

    state ROUTED {
        [*] --> under_review
        note right of ROUTED
            BOA assigned by role/scope
            Latency clock starts
        end note
    }

    ROUTED --> UNDER_REVIEW : BOA accepts assignment
    ROUTED --> ESCALATED : BOA out of scope / timeout

    state UNDER_REVIEW {
        [*] --> approved
        [*] --> rejected
        [*] --> escalated
        note right of UNDER_REVIEW
            Standing authority examines
            Evidence cited, reasoning recorded
        end note
    }

    UNDER_REVIEW --> APPROVED : Override granted
    UNDER_REVIEW --> REJECTED : Override denied
    UNDER_REVIEW --> ESCALATED : Beyond BOA scope

    state APPROVED {
        [*] --> resolved
        note right of APPROVED
            Re-scoped parameters issued
            Operator coaching provided
        end note
    }

    state REJECTED {
        [*] --> resolved
        note right of REJECTED
            Boundary preserved
            Context reset required
        end note
    }

    state ESCALATED {
        [*] --> under_review
        [*] --> resolved
        note right of ESCALATED
            Higher authority invoked
            Or: auto-resolved after timeout
        end note
    }

    APPROVED --> RESOLVED : RRP Resolution Service
    REJECTED --> RESOLVED : RRP Resolution Service
    ESCALATED --> RESOLVED : Timeout / Final authority
    ESCALATED --> UNDER_REVIEW : Higher BOA accepts

    state RESOLVED {
        [*] --> archived
        note right of RESOLVED
            Thread closed
            State updated
            Audit level assigned
        end note
    }

    RESOLVED --> ARCHIVED : Retention period expired
    ARCHIVED --> [*]

    classDef vaig fill:#e74c3c,color:white,font-weight:bold
    classDef rrp fill:#3498db,color:white,font-weight:bold
    classDef boa fill:#2ecc71,color:white,font-weight:bold
    classDef terminal fill:#95a5a6,color:white

    class EMITTED vaig
    class ENRICHED,ROUTED,RESOLVED rrp
    class UNDER_REVIEW,APPROVED,REJECTED,ESCALATED boa
    class ARCHIVED terminal
```