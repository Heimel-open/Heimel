export type DemoDecision = "ALLOW" | "STEP_UP";

export type GuardianObservation =
  | "UNCHANGED"
  | "CHANGED_RECHECK"
  | "EVIDENCE_DEGRADED"
  | "SUPERSEDED"
  | "CONTEXT_MISMATCH"
  | "INSUFFICIENT_EVIDENCE";

export type StageState =
  | "PENDING"
  | "OBSERVED"
  | "CREATED"
  | "UNCHANGED"
  | "CHANGED_RECHECK"
  | "DELIVERED"
  | "ACKNOWLEDGED"
  | "VERIFIED";

export type ScenarioId = "evidence-unchanged" | "newer-clinical-state";

export type PipelineStageId =
  | "signal"
  | "alert"
  | "reht"
  | "routing"
  | "response"
  | "receipt";

export interface PipelineStage {
  id: PipelineStageId;
  label: string;
  owner: "Philips" | "VALO" | "Clinical team";
}

export interface DemoEvent {
  atMs: number;
  stage: PipelineStageId;
  title: string;
  detail: string;
  state?: Exclude<StageState, "PENDING">;
}

export interface EvidenceItem {
  label: string;
  value: string;
  tone: "neutral" | "pass" | "warn" | "fail";
}

export interface PatientContext {
  encounterToken: string;
  careArea: string;
  monitoringMode: string;
  sourceSystem: string;
}

export interface ClinicalReceipt {
  id: string;
  encounterToken: string;
  boundAlert: string;
  tScoreRef: string;
  tNotificationRef: string;
  tNextEventRef: string;
  stateHash: string;
  policyVersion: string;
  observation: GuardianObservation;
  decision: DemoDecision;
  verified: boolean;
}

export interface DemoScenario {
  id: ScenarioId;
  title: string;
  shortTitle: string;
  operatorIntent: string;
  boundaryMessage: string;
  finalDecision: DemoDecision;
  observation: GuardianObservation;
  accent: "green" | "amber";
  patient: PatientContext;
  events: DemoEvent[];
  evidence: EvidenceItem[];
  receipt: ClinicalReceipt;
  presenterScript: string[];
}

export const PIPELINE_STAGES: PipelineStage[] = [
  { id: "signal", label: "Patient signal", owner: "Philips" },
  { id: "alert", label: "EWS alert", owner: "Philips" },
  { id: "reht", label: "Evidence check", owner: "VALO" },
  { id: "routing", label: "Alert routing", owner: "Philips" },
  { id: "response", label: "Clinical response", owner: "Clinical team" },
  { id: "receipt", label: "Governance receipt", owner: "VALO" },
];

const SHARED_PATIENT: PatientContext = {
  encounterToken: "encounter:demo-7f2a",
  careArea: "General ward / zone B",
  monitoringMode: "Guardian-style EWS monitoring",
  sourceSystem: "Philips patient monitoring",
};

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "evidence-unchanged",
    title: "The alert still matches the patient state",
    shortTitle: "Evidence unchanged",
    operatorIntent:
      "A Philips EWS alert is created, the underlying evidence remains current, and the assigned clinician acknowledges it.",
    boundaryMessage:
      "Philips owns detection, alert delivery, and acknowledgement. VALO only verifies whether the recorded alert can still be relied on at this point in the workflow.",
    finalDecision: "ALLOW",
    observation: "UNCHANGED",
    accent: "green",
    patient: SHARED_PATIENT,
    events: [
      {
        atMs: 0,
        stage: "signal",
        title: "T0 — monitored state recorded",
        detail: "Pseudonymous measurements and signal-quality metadata are bound to EWS event ews-1042.",
        state: "OBSERVED",
      },
      {
        atMs: 900,
        stage: "alert",
        title: "T1 — Philips alert created",
        detail: "The hospital-owned EWS workflow creates notification alert-1042. VALO does not calculate or reinterpret the score.",
        state: "CREATED",
      },
      {
        atMs: 2100,
        stage: "reht",
        title: "REHT finds no material state change",
        detail: "Freshness, continuity, context, signal quality, and supersession checks remain satisfied.",
        state: "UNCHANGED",
      },
      {
        atMs: 3300,
        stage: "routing",
        title: "Philips routes the alert",
        detail: "The notification is delivered through the existing Philips clinical routing workflow.",
        state: "DELIVERED",
      },
      {
        atMs: 4500,
        stage: "response",
        title: "T2 — assigned clinician acknowledges",
        detail: "Human clinical authority remains intact. The demo makes no diagnosis or treatment recommendation.",
        state: "ACKNOWLEDGED",
      },
      {
        atMs: 5700,
        stage: "receipt",
        title: "RACS receipt verified",
        detail: "T0, T1, T2, policy version, evidence references, observation, and decision are hash-bound without direct identifiers.",
        state: "VERIFIED",
      },
    ],
    evidence: [
      { label: "Evidence freshness", value: "latest required evidence remains inside the validity window", tone: "pass" },
      { label: "State continuity", value: "no newer conflicting state before acknowledgement", tone: "pass" },
      { label: "Context continuity", value: "care area and workflow context unchanged", tone: "pass" },
      { label: "Signal quality", value: "source quality remains acceptable", tone: "pass" },
      { label: "Supersession", value: "no newer authoritative alert replaces alert-1042", tone: "pass" },
    ],
    receipt: {
      id: "racs-clinical-allow-01042",
      encounterToken: "encounter:demo-7f2a",
      boundAlert: "alert-1042",
      tScoreRef: "event:ews-1042",
      tNotificationRef: "event:alert-1042",
      tNextEventRef: "event:ack-1042",
      stateHash: "sha256:61f8f3e6b16a4d44",
      policyVersion: "guardian-ews-admissibility-v0.1",
      observation: "UNCHANGED",
      decision: "ALLOW",
      verified: true,
    },
    presenterScript: [
      "Philips detects the patient signal and creates the hospital-owned EWS alert.",
      "REHT does not judge the diagnosis. It checks whether the evidence behind the alert is still current when the workflow relies on it.",
      "Nothing material changed, so Philips routing and the clinician response continue normally.",
      "The receipt binds the alert, the latest state, the human acknowledgement, and the governance result without storing direct patient identifiers.",
    ],
  },
  {
    id: "newer-clinical-state",
    title: "The alert arrives after the patient state changed",
    shortTitle: "Newer state",
    operatorIntent:
      "The same Philips alert is created, but a newer measurement and care-context change occur before the workflow relies on it.",
    boundaryMessage:
      "The alert is not suppressed, delayed, or rewritten. Philips still routes it. VALO marks the reliance context CHANGED_RECHECK so the clinician sees that newer evidence exists.",
    finalDecision: "STEP_UP",
    observation: "CHANGED_RECHECK",
    accent: "amber",
    patient: SHARED_PATIENT,
    events: [
      {
        atMs: 0,
        stage: "signal",
        title: "T0 — monitored state recorded",
        detail: "The same pseudonymous EWS event ews-1042 is created from the original monitored state.",
        state: "OBSERVED",
      },
      {
        atMs: 900,
        stage: "alert",
        title: "T1 — Philips alert created",
        detail: "Notification alert-1042 enters the existing clinical alert workflow.",
        state: "CREATED",
      },
      {
        atMs: 1700,
        stage: "signal",
        title: "Newer evidence and context arrive",
        detail: "A later measurement is recorded and the encounter moves to a different care context before acknowledgement.",
        state: "OBSERVED",
      },
      {
        atMs: 2700,
        stage: "reht",
        title: "REHT marks CHANGED_RECHECK",
        detail: "The original alert is real, but its recorded evidence no longer represents the complete current state.",
        state: "CHANGED_RECHECK",
      },
      {
        atMs: 3900,
        stage: "routing",
        title: "Philips routes the alert unchanged",
        detail: "Shadow mode does not suppress or alter the clinical notification. The changed-state marker travels alongside the review context.",
        state: "DELIVERED",
      },
      {
        atMs: 5100,
        stage: "response",
        title: "T2 — clinician acknowledges with newer context visible",
        detail: "The next clinical judgment remains human. The workflow requires reassessment against the latest authoritative state.",
        state: "ACKNOWLEDGED",
      },
      {
        atMs: 6300,
        stage: "receipt",
        title: "STEP_UP receipt verified",
        detail: "The receipt records the state change, the unchanged Philips delivery path, and the requirement for human recheck.",
        state: "VERIFIED",
      },
    ],
    evidence: [
      { label: "Evidence freshness", value: "newer measurement exists after the original score", tone: "warn" },
      { label: "State continuity", value: "original and current state fingerprints differ", tone: "fail" },
      { label: "Context continuity", value: "care context changed before acknowledgement", tone: "warn" },
      { label: "Alert handling", value: "Philips alert delivered unchanged in shadow mode", tone: "pass" },
      { label: "Required next step", value: "human recheck against latest authoritative state", tone: "warn" },
    ],
    receipt: {
      id: "racs-clinical-stepup-01042",
      encounterToken: "encounter:demo-7f2a",
      boundAlert: "alert-1042",
      tScoreRef: "event:ews-1042",
      tNotificationRef: "event:alert-1042",
      tNextEventRef: "event:ack-1042-recheck",
      stateHash: "sha256:be7dd9a76a2081cf",
      policyVersion: "guardian-ews-admissibility-v0.1",
      observation: "CHANGED_RECHECK",
      decision: "STEP_UP",
      verified: true,
    },
    presenterScript: [
      "This starts with the same Philips alert, so the difference is not the alert engine.",
      "Before the alert is relied on, a newer measurement and a context change alter the patient-state record.",
      "VALO does not cancel the alarm or recommend treatment. It marks CHANGED_RECHECK and keeps the human clinical authority in control.",
      "The receipt proves that Philips delivered the alert, the state changed, and the next action required renewed human judgment.",
    ],
  },
];

export const SIMULATION_DISCLOSURE =
  "SIMULATED SHADOW DEMO — no diagnosis, treatment recommendation, alert suppression, or production control";

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

export function getStageState(
  scenario: DemoScenario,
  stageId: PipelineStageId,
  elapsedMs: number,
): StageState {
  const event = getVisibleEvents(scenario, elapsedMs)
    .filter((candidate) => candidate.stage === stageId)
    .at(-1);

  return event?.state ?? "PENDING";
}
