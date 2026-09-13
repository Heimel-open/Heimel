import { describe, expect, it } from "vitest";
import {
  DEMO_SCENARIOS,
  getActiveStageId,
  getScenarioDurationMs,
  getStageState,
  getVisibleEvents,
} from "./liveSystemDemoData";

describe("Philips patient monitoring demo data", () => {
  it("ships the two matched clinical replay scenarios", () => {
    expect(DEMO_SCENARIOS.map((scenario) => scenario.id)).toEqual([
      "evidence-unchanged",
      "newer-clinical-state",
    ]);

    expect(DEMO_SCENARIOS[0].patient.encounterToken).toBe(
      DEMO_SCENARIOS[1].patient.encounterToken,
    );
  });

  it("keeps each scenario deterministic, pseudonymous, and receipt-bound", () => {
    for (const scenario of DEMO_SCENARIOS) {
      const eventTimes = scenario.events.map((event) => event.atMs);

      expect(eventTimes).toEqual([...eventTimes].sort((a, b) => a - b));
      expect(scenario.patient.encounterToken).toMatch(/^encounter:/);
      expect(scenario.receipt.encounterToken).toBe(scenario.patient.encounterToken);
      expect(scenario.receipt.boundAlert).toBe("alert-1042");
      expect(scenario.receipt.policyVersion).toBe(
        "guardian-ews-admissibility-v0.1",
      );
      expect(scenario.receipt.verified).toBe(true);
      expect(getScenarioDurationMs(scenario)).toBeGreaterThan(
        eventTimes.at(-1) ?? 0,
      );
    }
  });

  it("allows reliance when the evidence remains unchanged", () => {
    const scenario = DEMO_SCENARIOS[0];

    expect(getStageState(scenario, "reht", 2300)).toBe("UNCHANGED");
    expect(getStageState(scenario, "routing", 3600)).toBe("DELIVERED");
    expect(scenario.observation).toBe("UNCHANGED");
    expect(scenario.finalDecision).toBe("ALLOW");
    expect(scenario.receipt.decision).toBe("ALLOW");
  });

  it("steps up on newer state without suppressing the Philips alert", () => {
    const scenario = DEMO_SCENARIOS[1];

    expect(getStageState(scenario, "reht", 3000)).toBe("CHANGED_RECHECK");
    expect(getStageState(scenario, "routing", 4200)).toBe("DELIVERED");
    expect(scenario.observation).toBe("CHANGED_RECHECK");
    expect(scenario.finalDecision).toBe("STEP_UP");
    expect(scenario.evidence).toContainEqual({
      label: "Alert handling",
      value: "Philips alert delivered unchanged in shadow mode",
      tone: "pass",
    });
  });

  it("reveals timed events and active stages deterministically", () => {
    const scenario = DEMO_SCENARIOS[1];

    expect(getVisibleEvents(scenario, 0)).toHaveLength(1);
    expect(getVisibleEvents(scenario, 1800)).toHaveLength(3);
    expect(getActiveStageId(scenario, 1800)).toBe("signal");
    expect(getActiveStageId(scenario, 3000)).toBe("reht");
  });
});
