export type DeviceExecutionVerdict = "ALLOW" | "DENY";
export type DeviceExecutionTone = "neutral" | "pass" | "warn" | "fail";

export const DEVICE_EXECUTION_STAGE_IDS = [
  "proposal",
  "identity",
  "attestation",
  "vaig",
  "reht",
  "racs",
  "receipt",
] as const;

export type DeviceExecutionStageId = (typeof DEVICE_EXECUTION_STAGE_IDS)[number];

export interface DeviceExecutionStage {
  id: DeviceExecutionStageId;
  label: string;
  atMs: number;
  result: string;
  tone: DeviceExecutionTone;
}

export interface DeviceExecutionEvent {
  atMs: number;
  source: string;
  title: string;
  detail: string;
  tone: DeviceExecutionTone;
}

export interface DeviceExecutionScenario {
  id: "compromised-proxy" | "authorized-maintenance";
  label: string;
  title: string;
  summary: string;
  verdict: DeviceExecutionVerdict;
  decisionReason: string;
  device: {
    id: string;
    asset: string;
    zone: string;
    identity: string;
  };
  request: {
    actor: string;
    action: string;
    destination: string;
    mandate: string;
  };
  attestation: {
    expected: string;
    observed: string;
    state: "ATTESTED" | "MISMATCH";
  };
  governance: {
    vaig: string;
    reht: DeviceExecutionVerdict;
    racs: "RELEASED" | "BLOCKED";
  };
  receipt: {
    receiptId: string;
    deviceDigest: string;
    actionDigest: string;
    policyVersion: string;
    executionOutcome: string;
    chainHash: string;
  };
  stages: DeviceExecutionStage[];
  events: DeviceExecutionEvent[];
}

export const DEVICE_EXECUTION_SCENARIOS: DeviceExecutionScenario[] = [
  {
    id: "compromised-proxy",
    label: "Compromised gateway",
    title: "A trusted device proposes an untrusted action.",
    summary:
      "An edge gateway with a valid hardware identity attempts to open an outbound tunnel after its measured boot state has changed. The request is outside the operator mandate.",
    verdict: "DENY",
    decisionReason:
      "The device identity is valid, but runtime state and requested destination are not admissible for this mandate. REHT denies release and RACS blocks the network change.",
    device: {
      id: "EDGE-GW-17",
      asset: "North Sea process unit — synthetic demo",
      zone: "OT Zone 2",
      identity: "TPM-bound certificate verified",
    },
    request: {
      actor: "Maintenance Agent MA-204",
      action: "Create a 30-minute outbound support tunnel",
      destination: "198.51.100.44:443 — outside approved destination set",
      mandate: "Read telemetry and publish summaries to the approved analytics broker",
    },
    attestation: {
      expected: "fw:3.4.2 / boot:91f2",
      observed: "fw:3.4.2 / boot:7c9a",
      state: "MISMATCH",
    },
    governance: {
      vaig: "Composite distrust 0.94 · critical evidence conflict",
      reht: "DENY",
      racs: "BLOCKED",
    },
    receipt: {
      receiptId: "rx_iot_20260803_001",
      deviceDigest: "sha256:3c76a4e7d93a",
      actionDigest: "sha256:b57fd6c0a82e",
      policyVersion: "VALO-DEVICE-EXEC-2026.08",
      executionOutcome: "NO_NETWORK_CHANGE",
      chainHash: "sha256:8a91e5d24c4f0a71",
    },
    stages: [
      { id: "proposal", label: "Proposed action", atMs: 0, result: "TUNNEL REQUESTED", tone: "warn" },
      { id: "identity", label: "Device identity", atMs: 700, result: "VERIFIED", tone: "pass" },
      { id: "attestation", label: "Runtime attestation", atMs: 1400, result: "MISMATCH", tone: "fail" },
      { id: "vaig", label: "VAIG evaluation", atMs: 2200, result: "CRITICAL", tone: "fail" },
      { id: "reht", label: "REHT clearance", atMs: 3000, result: "DENY", tone: "fail" },
      { id: "racs", label: "RACS enforcement", atMs: 3800, result: "BLOCKED", tone: "fail" },
      { id: "receipt", label: "Execution receipt", atMs: 4500, result: "SEALED", tone: "pass" },
    ],
    events: [
      { atMs: 0, source: "Agent", title: "Support tunnel proposed", detail: "The agent requests an outbound firewall change for EDGE-GW-17.", tone: "warn" },
      { atMs: 700, source: "Identity adapter", title: "Hardware identity verified", detail: "The certificate is valid and bound to the expected TPM-backed device key.", tone: "pass" },
      { atMs: 1400, source: "Attestation adapter", title: "Measured boot differs", detail: "Observed boot digest 7c9a does not match approved baseline 91f2.", tone: "fail" },
      { atMs: 2200, source: "VAIG", title: "Evidence conflict evaluated", detail: "Runtime state is untrusted and the destination is outside the approved target set.", tone: "fail" },
      { atMs: 3000, source: "REHT", title: "Clearance denied", detail: "Valid identity does not override missing authority or failed state attestation.", tone: "fail" },
      { atMs: 3800, source: "RACS", title: "Execution blocked", detail: "No firewall rule, tunnel credential or one-time permit is released.", tone: "fail" },
      { atMs: 4500, source: "Receipt adapter", title: "Denied execution sealed", detail: "Device, action, evidence, decision and outcome are bound into one synthetic receipt.", tone: "pass" },
    ],
  },
  {
    id: "authorized-maintenance",
    label: "Authorized maintenance",
    title: "The same boundary permits a valid action.",
    summary:
      "A known gateway with an approved measured state publishes a bounded vibration summary to the authorized analytics broker under a current maintenance mandate.",
    verdict: "ALLOW",
    decisionReason:
      "Identity, runtime state, destination, action scope and operator mandate all match. REHT clears the bounded action and RACS releases a one-time permit.",
    device: {
      id: "EDGE-GW-05",
      asset: "North Sea process unit — synthetic demo",
      zone: "OT Zone 2",
      identity: "TPM-bound certificate verified",
    },
    request: {
      actor: "Maintenance Agent MA-118",
      action: "Upload a signed vibration summary",
      destination: "analytics-broker.demo:443 — approved",
      mandate: "Publish vibration summaries for compressor C-12 until 18:00 UTC",
    },
    attestation: {
      expected: "fw:3.4.2 / boot:91f2",
      observed: "fw:3.4.2 / boot:91f2",
      state: "ATTESTED",
    },
    governance: {
      vaig: "Composite distrust 0.08 · evidence complete",
      reht: "ALLOW",
      racs: "RELEASED",
    },
    receipt: {
      receiptId: "rx_iot_20260803_002",
      deviceDigest: "sha256:901e4d2c77aa",
      actionDigest: "sha256:6f1023ad7c91",
      policyVersion: "VALO-DEVICE-EXEC-2026.08",
      executionOutcome: "TELEMETRY_UPLOAD_ACCEPTED",
      chainHash: "sha256:20bc9b6ca81031d4",
    },
    stages: [
      { id: "proposal", label: "Proposed action", atMs: 0, result: "UPLOAD REQUESTED", tone: "neutral" },
      { id: "identity", label: "Device identity", atMs: 700, result: "VERIFIED", tone: "pass" },
      { id: "attestation", label: "Runtime attestation", atMs: 1400, result: "ATTESTED", tone: "pass" },
      { id: "vaig", label: "VAIG evaluation", atMs: 2200, result: "COMPLETE", tone: "pass" },
      { id: "reht", label: "REHT clearance", atMs: 3000, result: "ALLOW", tone: "pass" },
      { id: "racs", label: "RACS enforcement", atMs: 3800, result: "RELEASED", tone: "pass" },
      { id: "receipt", label: "Execution receipt", atMs: 4500, result: "SEALED", tone: "pass" },
    ],
    events: [
      { atMs: 0, source: "Agent", title: "Telemetry upload proposed", detail: "The request is bound to gateway EDGE-GW-05 and compressor C-12.", tone: "neutral" },
      { atMs: 700, source: "Identity adapter", title: "Hardware identity verified", detail: "The device certificate and TPM-backed key match the registered gateway.", tone: "pass" },
      { atMs: 1400, source: "Attestation adapter", title: "Runtime state attested", detail: "Firmware and measured boot match the approved operational baseline.", tone: "pass" },
      { atMs: 2200, source: "VAIG", title: "Evidence evaluated", detail: "Action, target, time window and evidence satisfy the evaluation contract.", tone: "pass" },
      { atMs: 3000, source: "REHT", title: "Bounded action cleared", detail: "The proposed upload is admissible here, now, by this actor and device.", tone: "pass" },
      { atMs: 3800, source: "RACS", title: "One-time permit released", detail: "The permit is bound to the action digest, destination and current attestation.", tone: "pass" },
      { atMs: 4500, source: "Receipt adapter", title: "Execution outcome sealed", detail: "The accepted upload and its verified outcome are recorded in the synthetic receipt.", tone: "pass" },
    ],
  },
];

export function getDeviceScenarioDurationMs(scenario: DeviceExecutionScenario): number {
  return (scenario.events.at(-1)?.atMs ?? 0) + 900;
}

export function getVisibleDeviceEvents(
  scenario: DeviceExecutionScenario,
  elapsedMs: number,
): DeviceExecutionEvent[] {
  return scenario.events.filter((event) => event.atMs <= elapsedMs);
}

export function getActiveDeviceStageId(
  scenario: DeviceExecutionScenario,
  elapsedMs: number,
): DeviceExecutionStageId {
  return scenario.stages.reduce<DeviceExecutionStageId>((active, stage) => {
    return stage.atMs <= elapsedMs ? stage.id : active;
  }, scenario.stages[0].id);
}
