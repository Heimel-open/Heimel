import { describe, expect, it } from "vitest";
import {
  DEMO_SCENARIOS,
  getActiveStageId,
  getScenarioDurationMs,
  getStageVerdict,
  getVisibleEvents,
} from "./valoLiveDemoData";

describe("live system demo scenario data", () => {
  it("ships the three commissioned deterministic scenarios", () => {
    expect(DEMO_SCENARIOS.map((scenario) => scenario.id)).toEqual([
      "valid-consequential-merge",
      "business-authority-mismatch",
      "stale-clearance",
    ]);
  });

  it("keeps each scenario timeline monotonic and receipt-bound", () => {
    for (const scenario of DEMO_SCENARIOS) {
      const eventTimes = scenario.events.map((event) => event.atMs);
      expect(eventTimes).toEqual([...eventTimes].sort((a, b) => a - b));
      expect(scenario.receipt.boundAction.length).toBeGreaterThan(8);
      expect(scenario.receipt.commitSha).toMatch(/^[a-f0-9]{7}$/);
      expect(scenario.receipt.policyVersion).toBe("VALO-GOV-2026.07");
      expect(getScenarioDurationMs(scenario)).toBeGreaterThan(eventTimes.at(-1) ?? 0);
    }
  });

  it("models Scenario B as technically eligible but business-denied", () => {
    const scenario = DEMO_SCENARIOS[1];

    expect(getStageVerdict(scenario, "validator", 1200)).toBe("ALLOW");
    expect(getStageVerdict(scenario, "reht", 3600)).toBe("DENY");
    expect(getStageVerdict(scenario, "core", 5000)).toBe("DENY");
    expect(scenario.evidence).toContainEqual({
      label: "Core result",
      value: "COMMIT_BLOCKED",
      tone: "fail",
    });
  });

  it("reveals timed events and active stage deterministically", () => {
    const scenario = DEMO_SCENARIOS[2];

    expect(getVisibleEvents(scenario, 0)).toHaveLength(1);
    expect(getVisibleEvents(scenario, 2300)).toHaveLength(3);
    expect(getActiveStageId(scenario, 2300)).toBe("vaig");
  });
});
