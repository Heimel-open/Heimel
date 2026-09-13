import { describe, it, expect } from "vitest";
import {
  canTransition,
  canStateTransition,
  isSettled,
  LIFECYCLE_TRANSITIONS,
  type LifecyclePhase,
} from "./governedLifecycle";

describe("governed lifecycle — canTransition (VALO gate, no phase skipping)", () => {
  const allPhases: LifecyclePhase[] = [
    "DRAFT",
    "GATED",
    "QUEUED",
    "LEARNED",
    "WATCHLISTED",
  ];

  it("allows the documented forward transition DRAFT -> GATED", () => {
    expect(canTransition("DRAFT", "GATED")).toBe(true);
  });

  it("rejects skipping phases (DRAFT -> QUEUED is not allowed)", () => {
    expect(canTransition("DRAFT", "QUEUED")).toBe(false);
  });

  it("rejects illegal jumps across the lifecycle (e.g. GATED -> LEARNED)", () => {
    expect(canTransition("GATED", "LEARNED")).toBe(false);
  });

  it("allows gate reject back to DRAFT (GATED -> DRAFT)", () => {
    expect(canTransition("GATED", "DRAFT")).toBe(true);
  });

  it("allows approved QUEUED -> LEARNED", () => {
    expect(canTransition("QUEUED", "LEARNED")).toBe(true);
  });

  it("allows LEARNED -> WATCHLISTED", () => {
    expect(canTransition("LEARNED", "WATCHLISTED")).toBe(true);
  });

  it("WATCHLISTED is terminal-ish (only self-transition)", () => {
    expect(canTransition("WATCHLISTED", "WATCHLISTED")).toBe(true);
    expect(canTransition("WATCHLISTED", "DRAFT")).toBe(false);
    expect(canTransition("WATCHLISTED", "GATED")).toBe(false);
  });

  it("every phase's allowed targets match the canonical transition table", () => {
    for (const from of allPhases) {
      for (const to of allPhases) {
        expect(canTransition(from, to)).toBe(
          LIFECYCLE_TRANSITIONS[from].includes(to),
        );
      }
    }
  });

  it("rejects transitioning to the same non-self phase (no silent repeat)", () => {
    expect(canTransition("DRAFT", "DRAFT")).toBe(false);
    expect(canTransition("GATED", "GATED")).toBe(false);
    expect(canTransition("QUEUED", "QUEUED")).toBe(false);
    expect(canTransition("LEARNED", "LEARNED")).toBe(true); // LEARNED allows re-learn
  });
});

describe("governed lifecycle — isSettled", () => {
  it("LEARNED and WATCHLISTED are settled", () => {
    expect(isSettled({ phase: "LEARNED", draftId: "x", behaviorTags: [], distrustLevel: 0 })).toBe(true);
    expect(isSettled({ phase: "WATCHLISTED", contactId: "c", flagType: "monitor" })).toBe(true);
  });

  it("DRAFT, GATED, QUEUED are not settled", () => {
    expect(isSettled({ phase: "DRAFT", content: "x", channel: "post", createdAt: 0 })).toBe(false);
    expect(isSettled({ phase: "GATED", draftId: "d", integrity: {} as any, gateDecision: "CLEAR", worm: {} as any })).toBe(false);
    expect(isSettled({ phase: "QUEUED", draftId: "d", queueState: "pending" })).toBe(false);
  });
});

describe("governed lifecycle — canStateTransition (gate decisions & approval state)", () => {
  it("allows GATED -> QUEUED only for CLEAR or WATCH decisions", () => {
    const clearState = { phase: "GATED", draftId: "d1", integrity: {} as any, gateDecision: "CLEAR", worm: {} as any } as const;
    const watchState = { phase: "GATED", draftId: "d2", integrity: {} as any, gateDecision: "WATCH", worm: {} as any } as const;
    const lockState = { phase: "GATED", draftId: "d3", integrity: {} as any, gateDecision: "LOCK", worm: {} as any } as const;
    const councilState = { phase: "GATED", draftId: "d4", integrity: {} as any, gateDecision: "COUNCIL", worm: {} as any } as const;

    expect(canStateTransition(clearState, "QUEUED")).toBe(true);
    expect(canStateTransition(watchState, "QUEUED")).toBe(true);
    expect(canStateTransition(lockState, "QUEUED")).toBe(false);
    expect(canStateTransition(councilState, "QUEUED")).toBe(false);
  });

  it("allows GATED -> DRAFT regardless of gate decision (rejection path)", () => {
    const lockState = { phase: "GATED", draftId: "d3", integrity: {} as any, gateDecision: "LOCK", worm: {} as any } as const;
    expect(canStateTransition(lockState, "DRAFT")).toBe(true);
  });

  it("allows QUEUED -> LEARNED only for approved queue state", () => {
    const approved = { phase: "QUEUED", draftId: "q1", queueState: "approved" } as const;
    const pending = { phase: "QUEUED", draftId: "q2", queueState: "pending" } as const;
    const rejected = { phase: "QUEUED", draftId: "q3", queueState: "rejected" } as const;

    expect(canStateTransition(approved, "LEARNED")).toBe(true);
    expect(canStateTransition(pending, "LEARNED")).toBe(false);
    expect(canStateTransition(rejected, "LEARNED")).toBe(false);
  });
});

