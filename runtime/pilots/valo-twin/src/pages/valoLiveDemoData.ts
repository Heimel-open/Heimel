export type DemoVerdict = "ALLOW" | "DENY";

export type ScenarioId =
  | "valid-consequential-merge"
  | "business-authority-mismatch"
  | "stale-clearance";

export type PipelineStageId =
  | "request"
  | "validator"
  | "vaig"
  | "reht"
  | "core"
  | "racs";

export interface PipelineStage {
  id: PipelineStageId;
  label: string;
}

export interface DemoEvent {
  atMs: number;
  stage: PipelineStageId;
  title: string;
  detail: string;
  verdict?: DemoVerdict;
}

export interface EvidenceItem {
  label: string;
  value: string;
  tone: "neutral" | "pass" | "warn" | "fail";
}

export interface RacsReceipt {
  id: string;
  boundAction: string;
  commitSha: string;
  stateHash: string;
  policyVersion: string;
  decision: DemoVerdict;
}

export interface DemoScenario {
  id: ScenarioId;
  title: string;
  shortTitle: string;
  operatorIntent: string;
  finalVerdict: DemoVerdict;
  finalMessage: string;
  accent: "green" | "red" | "amber";
  events: DemoEvent[];
  evidence: EvidenceItem[];
  receipt: RacsReceipt;
  presenterScript: string[];
}

export const PIPELINE_STAGES: PipelineStage[] = [
  { id: "request", label: "Request" },
  { id: "validator", label: "Validator" },
  { id: "vaig", label: "VAIG" },
  { id: "reht", label: "REHT" },
  { id: "core", label: "Core" },
  { id: "racs", label: "RACS" },
];

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "valid-consequential-merge",
    title: "Valid consequential merge",
    shortTitle: "Valid merge",
    operatorIntent: "Merge PR 41 after CI, reviewer, and scope clearance match the live commit.",
    finalVerdict: "ALLOW",
    finalMessage: "Core applies the merge because every governing fact is current and bound to the action.",
    accent: "green",
    events: [
      {
        atMs: 0,
        stage: "request",
        title: "Operator requests merge",
        detail: "Action target is PR 41 at commit 9f31c2a.",
      },
      {
        atMs: 1100,
        stage: "validator",
        title: "Validator confirms technical eligibility",
        detail: "Required checks are green and the branch is mergeable.",
        verdict: "ALLOW",
      },
      {
        atMs: 2300,
        stage: "vaig",
        title: "VAIG confirms consequential scope",
        detail: "The requested merge is inside the approved deployment lane.",
        verdict: "ALLOW",
      },
      {
        atMs: 3500,
        stage: "reht",
        title: "REHT clears authority",
        detail: "Reviewer authority, labels, and decision window match policy VALO-GOV-2026.07.",
        verdict: "ALLOW",
      },
      {
        atMs: 4700,
        stage: "core",
        title: "Core executes governed merge",
        detail: "The live head commit matches the clearance-bound commit.",
        verdict: "ALLOW",
      },
      {
        atMs: 5900,
        stage: "racs",
        title: "RACS records receipt",
        detail: "Decision, commit, state hash, and action hash are sealed.",
        verdict: "ALLOW",
      },
    ],
    evidence: [
      { label: "CI", value: "all required checks passed", tone: "pass" },
      { label: "Authority", value: "release owner matched", tone: "pass" },
      { label: "Commit binding", value: "9f31c2a == live head", tone: "pass" },
      { label: "Policy", value: "VALO-GOV-2026.07", tone: "neutral" },
    ],
    receipt: {
      id: "racs-live-allow-00041",
      boundAction: "merge:nsolland/Valo-Twin#41",
      commitSha: "9f31c2a",
      stateHash: "sha256:61f8f3e6b16a4d44",
      policyVersion: "VALO-GOV-2026.07",
      decision: "ALLOW",
    },
    presenterScript: [
      "This is the happy path: a real operator asks for a consequential merge.",
      "The validator only proves technical eligibility; it does not grant business authority.",
      "VAIG and REHT confirm scope and authority before Core can act.",
      "RACS closes the loop by preserving a receipt that binds the decision to the exact action.",
    ],
  },
  {
    id: "business-authority-mismatch",
    title: "Technical launch allowed, business action denied",
    shortTitle: "Authority mismatch",
    operatorIntent: "Promote a technically valid launch even though business authority is missing.",
    finalVerdict: "DENY",
    finalMessage: "Core blocks the business action after REHT denies the authority match.",
    accent: "red",
    events: [
      {
        atMs: 0,
        stage: "request",
        title: "Launch request arrives",
        detail: "The build artifact is valid and signed.",
      },
      {
        atMs: 1000,
        stage: "validator",
        title: "Validator finds no technical blocker",
        detail: "Artifact, branch protection, and smoke checks pass.",
        verdict: "ALLOW",
      },
      {
        atMs: 2200,
        stage: "vaig",
        title: "VAIG flags consequential launch",
        detail: "This action changes a public demo surface and requires delegated release authority.",
        verdict: "DENY",
      },
      {
        atMs: 3400,
        stage: "reht",
        title: "REHT denies authority",
        detail: "The requester can build the demo but cannot approve the launch.",
        verdict: "DENY",
      },
      {
        atMs: 4600,
        stage: "core",
        title: "Core returns COMMIT_BLOCKED",
        detail: "No production mutation is attempted after the authority denial.",
        verdict: "DENY",
      },
      {
        atMs: 5800,
        stage: "racs",
        title: "RACS records denied receipt",
        detail: "The denial is inspectable with validator findings and authority reason.",
        verdict: "DENY",
      },
    ],
    evidence: [
      { label: "Technical gate", value: "eligible", tone: "pass" },
      { label: "Business authority", value: "release delegate missing", tone: "fail" },
      { label: "Core result", value: "COMMIT_BLOCKED", tone: "fail" },
      { label: "Mutation policy", value: "none attempted", tone: "pass" },
    ],
    receipt: {
      id: "racs-live-deny-00012",
      boundAction: "launch:demo/live-system",
      commitSha: "4a77d08",
      stateHash: "sha256:905d7cf4d2510e10",
      policyVersion: "VALO-GOV-2026.07",
      decision: "DENY",
    },
    presenterScript: [
      "This is the media-critical story: technical readiness is not the same as authority.",
      "The validator can say the launch is buildable while VAIG marks it consequential.",
      "REHT denies the business action, and Core turns that into COMMIT_BLOCKED.",
      "The receipt proves both facts: the artifact was eligible, and the action was denied.",
    ],
  },
  {
    id: "stale-clearance",
    title: "Previously issued clearance invalidated by state change",
    shortTitle: "Stale clearance",
    operatorIntent: "Reuse yesterday's clearance after the branch head and policy state changed.",
    finalVerdict: "DENY",
    finalMessage: "Core refuses to execute because the clearance no longer matches live state.",
    accent: "amber",
    events: [
      {
        atMs: 0,
        stage: "request",
        title: "Operator replays old clearance",
        detail: "Clearance was issued for commit 18bb90c.",
      },
      {
        atMs: 1000,
        stage: "validator",
        title: "Validator detects changed head",
        detail: "Live branch now points to 31c0af9.",
        verdict: "DENY",
      },
      {
        atMs: 2200,
        stage: "vaig",
        title: "VAIG marks stale consequential evidence",
        detail: "The clearance bundle does not cover the current action state.",
        verdict: "DENY",
      },
      {
        atMs: 3400,
        stage: "reht",
        title: "REHT invalidates prior approval",
        detail: "Approval must be refreshed against the new commit and state hash.",
        verdict: "DENY",
      },
      {
        atMs: 4600,
        stage: "core",
        title: "Core blocks stale commit path",
        detail: "The action hash changed after clearance was issued.",
        verdict: "DENY",
      },
      {
        atMs: 5800,
        stage: "racs",
        title: "RACS stores invalidation receipt",
        detail: "The stale clearance remains auditable without being executable.",
        verdict: "DENY",
      },
    ],
    evidence: [
      { label: "Cleared commit", value: "18bb90c", tone: "neutral" },
      { label: "Live commit", value: "31c0af9", tone: "warn" },
      { label: "State hash", value: "changed after clearance", tone: "fail" },
      { label: "Required action", value: "refresh approval", tone: "warn" },
    ],
    receipt: {
      id: "racs-stale-deny-00007",
      boundAction: "merge:nsolland/Valo-Twin#38",
      commitSha: "31c0af9",
      stateHash: "sha256:be7dd9a76a2081cf",
      policyVersion: "VALO-GOV-2026.07",
      decision: "DENY",
    },
    presenterScript: [
      "This path shows why VALO binds approvals to live facts, not vibes.",
      "A clearance that was true yesterday cannot be replayed after commit or state drift.",
      "The system blocks the action and records why the old approval became non-executable.",
      "That gives operators a clean next move: refresh the clearance against current state.",
    ],
  },
];

export const SIMULATION_DISCLOSURE =
  "SIMULATED SYSTEM DEMO - presentation only, no production mutations";

export function getDemoScenario(id: ScenarioId): DemoScenario {
  return DEMO_SCENARIOS.find((scenario) => scenario.id === id) ?? DEMO_SCENARIOS[0];
}

export function getScenarioDurationMs(scenario: DemoScenario): number {
  return Math.max(...scenario.events.map((event) => event.atMs)) + 1400;
}

export function getVisibleEvents(scenario: DemoScenario, elapsedMs: number): DemoEvent[] {
  return scenario.events.filter((event) => event.atMs <= elapsedMs);
}

export function getActiveStageId(scenario: DemoScenario, elapsedMs: number): PipelineStageId {
  const visible = getVisibleEvents(scenario, elapsedMs);
  return visible.at(-1)?.stage ?? scenario.events[0].stage;
}

export function getStageVerdict(
  scenario: DemoScenario,
  stageId: PipelineStageId,
  elapsedMs: number,
): DemoVerdict | "PENDING" {
  const event = getVisibleEvents(scenario, elapsedMs)
    .filter((candidate) => candidate.stage === stageId)
    .at(-1);

  return event?.verdict ?? "PENDING";
}
