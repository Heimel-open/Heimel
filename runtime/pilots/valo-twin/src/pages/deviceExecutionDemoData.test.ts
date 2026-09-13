import { describe, expect, it } from "vitest";
import {
  DEVICE_EXECUTION_SCENARIOS,
  DEVICE_EXECUTION_STAGE_IDS,
  getActiveDeviceStageId,
  getDeviceScenarioDurationMs,
  getVisibleDeviceEvents,
} from "./deviceExecutionDemoData";

describe("attributed device execution demo data", () => {
  it("ships one denied and one allowed synthetic scenario", () => {
    expect(DEVICE_EXECUTION_SCENARIOS.map((scenario) => [scenario.id, scenario.verdict])).toEqual([
      ["compromised-proxy", "DENY"],
      ["authorized-maintenance", "ALLOW"],
    ]);
  });

  it("keeps the full device-to-receipt chain in every scenario", () => {
    for (const scenario of DEVICE_EXECUTION_SCENARIOS) {
      expect(scenario.stages.map((stage) => stage.id)).toEqual(DEVICE_EXECUTION_STAGE_IDS);
      expect(scenario.events.map((event) => event.atMs)).toEqual(
        [...scenario.events.map((event) => event.atMs)].sort((a, b) => a - b),
      );
      expect(scenario.receipt.deviceDigest).toMatch(/^sha256:[a-f0-9]+$/);
      expect(scenario.receipt.actionDigest).toMatch(/^sha256:[a-f0-9]+$/);
      expect(scenario.receipt.chainHash).toMatch(/^sha256:[a-f0-9]+$/);
      expect(getDeviceScenarioDurationMs(scenario)).toBeGreaterThan(
        scenario.events.at(-1)?.atMs ?? 0,
      );
    }
  });

  it("never models a denied request as released", () => {
    const denied = DEVICE_EXECUTION_SCENARIOS.find(
      (scenario) => scenario.id === "compromised-proxy",
    );

    expect(denied?.attestation.state).toBe("MISMATCH");
    expect(denied?.governance.reht).toBe("DENY");
    expect(denied?.governance.racs).toBe("BLOCKED");
    expect(denied?.receipt.executionOutcome).toBe("NO_NETWORK_CHANGE");
  });

  it("binds the allowed action to attested state and a released outcome", () => {
    const allowed = DEVICE_EXECUTION_SCENARIOS.find(
      (scenario) => scenario.id === "authorized-maintenance",
    );

    expect(allowed?.attestation.state).toBe("ATTESTED");
    expect(allowed?.attestation.expected).toBe(allowed?.attestation.observed);
    expect(allowed?.governance.reht).toBe("ALLOW");
    expect(allowed?.governance.racs).toBe("RELEASED");
  });

  it("reveals evidence and active stages deterministically", () => {
    const scenario = DEVICE_EXECUTION_SCENARIOS[0];

    expect(getVisibleDeviceEvents(scenario, 0)).toHaveLength(1);
    expect(getVisibleDeviceEvents(scenario, 2200)).toHaveLength(4);
    expect(getActiveDeviceStageId(scenario, 2200)).toBe("vaig");
  });
});
