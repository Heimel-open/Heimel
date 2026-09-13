-- VALO MCP Gateway — Parable-inspired extensions
-- Adds: plans, gates, delegations, reviews, ensemble runs

CREATE TABLE IF NOT EXISTS plans (
    plan_id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    intent TEXT NOT NULL,
    evidence_ids TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft', -- draft | approved | in_progress | done | cancelled
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS gates (
    gate_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    name TEXT NOT NULL,
    check_type TEXT NOT NULL, -- evidence | command_output | review | ensemble
    required BOOLEAN DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'pending', -- pending | passed | failed | skipped
    evidence_ids TEXT,
    output_ref TEXT,
    FOREIGN KEY(plan_id) REFERENCES plans(plan_id)
);

CREATE TABLE IF NOT EXISTS delegations (
    delegation_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    gate_id TEXT NOT NULL,
    actor TEXT NOT NULL,        -- director
    worker TEXT NOT NULL,       -- worker model/agent
    brief TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending | accepted | done | rejected
    created_at REAL NOT NULL,
    completed_at REAL,
    result_ref TEXT,
    FOREIGN KEY(plan_id) REFERENCES plans(plan_id),
    FOREIGN KEY(gate_id) REFERENCES gates(gate_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    delegation_id TEXT NOT NULL,
    reviewer TEXT NOT NULL,     -- stronger model or human
    verdict TEXT NOT NULL,      -- approve | revise | reject
    notes TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY(delegation_id) REFERENCES delegations(delegation_id)
);

CREATE TABLE IF NOT EXISTS ensemble_runs (
    ensemble_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    gate_id TEXT NOT NULL,
    agents TEXT NOT NULL,       -- JSON array of worker ids
    brief TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    created_at REAL NOT NULL,
    completed_at REAL,
    result_ref TEXT,
    FOREIGN KEY(plan_id) REFERENCES plans(plan_id),
    FOREIGN KEY(gate_id) REFERENCES gates(gate_id)
);

CREATE TABLE IF NOT EXISTS contradictions (
    contradiction_id TEXT PRIMARY KEY,
    ensemble_id TEXT NOT NULL,
    agent_a TEXT NOT NULL,
    agent_b TEXT NOT NULL,
    topic TEXT NOT NULL,
    resolution TEXT,            -- accepted | ignored | pending
    created_at REAL NOT NULL,
    FOREIGN KEY(ensemble_id) REFERENCES ensemble_runs(ensemble_id)
);

CREATE INDEX IF NOT EXISTS idx_plans_actor ON plans(actor);
CREATE INDEX IF NOT EXISTS idx_gates_plan ON gates(plan_id);
CREATE INDEX IF NOT EXISTS idx_delegations_plan ON delegations(plan_id);
CREATE INDEX IF NOT EXISTS idx_reviews_delegation ON reviews(delegation_id);
CREATE INDEX IF NOT EXISTS idx_ensemble_plan ON ensemble_runs(plan_id);
CREATE INDEX IF NOT EXISTS idx_contradictions_ensemble ON contradictions(ensemble_id);
