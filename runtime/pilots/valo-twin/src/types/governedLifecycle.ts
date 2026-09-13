/**
 * Governed Content Lifecycle — type layer for Valo-Twin (Valo-Twin #8).
 *
 * Binds the four operator routers (draft / queue / learn / watchlist) into one
 * type-safe governed content lifecycle. This is a TYPES-ONLY integration: it
 * describes the lifecycle states and transitions, it does NOT implement VAIG or
 * BARO logic (those belong in their own repos; Valo-Twin is UI/demo only).
 *
 * The lifecycle mirrors VALO's governed flow:
 *   DRAFT -> GATED (VALO 8-instrument gate) -> QUEUED (approval) ->
 *   LEARNED (behavioral analysis) -> WATCHLISTED (contact tracking)
 *
 * Each phase carries the existing Valo-Twin integrity types, so the UI can
 * render the whole governed path with one coherent state machine.
 */

import type { IntegrityResult, DistrustLevel, WORMEntry } from "./valo";

/** The four operator phases Valo-Twin exposes, as a lifecycle. */
export type LifecyclePhase =
  | "DRAFT"
  | "GATED"
  | "QUEUED"
  | "LEARNED"
  | "WATCHLISTED";

/** Allowed forward transitions (governed: no skipping phases). */
export const LIFECYCLE_TRANSITIONS: Record<LifecyclePhase, LifecyclePhase[]> = {
  DRAFT: ["GATED"],
  GATED: ["QUEUED", "DRAFT"], // gate pass -> queue; gate reject -> back to draft
  QUEUED: ["LEARNED", "DRAFT"], // approved -> learn; rejected -> back to draft
  LEARNED: ["WATCHLISTED", "LEARNED"], // analysis -> watchlist; re-learn
  WATCHLISTED: ["WATCHLISTED"], // terminal-ish: contact stays tracked
};

export interface LifecycleDraft {
  phase: "DRAFT";
  content: string;
  channel: "reply" | "dm" | "post" | "redteam";
  createdAt: number;
}

export interface LifecycleGated {
  phase: "GATED";
  draftId: string;
  integrity: IntegrityResult; // from the 8-instrument VALO gate
  gateDecision: "CLEAR" | "WATCH" | "FRICTION" | "COUNCIL" | "LOCK";
  worm: WORMEntry;
}

export interface LifecycleQueued {
  phase: "QUEUED";
  draftId: string;
  queueState: "pending" | "approved" | "rejected";
  reviewer?: string;
}

export interface LifecycleLearned {
  phase: "LEARNED";
  draftId: string;
  behaviorTags: string[];
  distrustLevel: DistrustLevel; // D0-D4 (never bare L0-L4)
}

export interface LifecycleWatchlisted {
  phase: "WATCHLISTED";
  contactId: string;
  flagType: "engaged" | "blocked" | "priority" | "monitor";
}

export type GovernedContentLifecycle =
  | LifecycleDraft
  | LifecycleGated
  | LifecycleQueued
  | LifecycleLearned
  | LifecycleWatchlisted;

/** Type guard: is this state a terminal/settled phase? */
export function isSettled(state: GovernedContentLifecycle): boolean {
  return state.phase === "WATCHLISTED" || state.phase === "LEARNED";
}

/** Validate a lifecycle phase transition at the type level. */
export function canTransition(
  from: LifecyclePhase,
  to: LifecyclePhase,
): boolean {
  return LIFECYCLE_TRANSITIONS[from].includes(to);
}

/**
 * Validate a full state transition considering gate decision and approval state (Valo-Twin #11).
 */
export function canStateTransition(
  fromState: GovernedContentLifecycle,
  toPhase: LifecyclePhase,
): boolean {
  if (!canTransition(fromState.phase, toPhase)) {
    return false;
  }

  // GATED -> QUEUED requires gate clearance (CLEAR or WATCH)
  if (fromState.phase === "GATED" && toPhase === "QUEUED") {
    return (
      fromState.gateDecision === "CLEAR" || fromState.gateDecision === "WATCH"
    );
  }

  // QUEUED -> LEARNED requires human approval
  if (fromState.phase === "QUEUED" && toPhase === "LEARNED") {
    return fromState.queueState === "approved";
  }

  return true;
}

