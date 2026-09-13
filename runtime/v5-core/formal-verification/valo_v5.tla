---- MODULE valo_v5 ----
EXTENDS Integers, Sequences, TLC

CONSTANTS MaxDegradedTime   \* Bound for degraded-state countdown (= 30 in valo_v5.cfg)

VARIABLES state, distrust_level, timer

vars == <<state, distrust_level, timer>>

(* Definere gyldige tilstander og tillitsnivåer *)
States == {"ACTIVE", "DEGRADED", "HALT"}
DistrustLevels == 0..4

(* Initialtilstand *)
Init ==
    /\ state = "ACTIVE"
    /\ distrust_level = 0
    /\ timer = 0

(* Regler for tilstandsoverganger *)
Next ==
    (* L3 Context Engine raises distrust non-deterministically *)
    \/ /\ state \in {"ACTIVE", "DEGRADED"}
       /\ distrust_level < 4
       /\ distrust_level' = distrust_level + 1
       /\ UNCHANGED <<state, timer>>

    (* L3 Context Engine lowers distrust on recovery *)
    \/ /\ state = "ACTIVE"
       /\ distrust_level > 0
       /\ distrust_level' = distrust_level - 1
       /\ UNCHANGED <<state, timer>>

    (* ACTIVE -> DEGRADED when distrust reaches warning threshold *)
    \/ /\ state = "ACTIVE"
       /\ distrust_level >= 3
       /\ state' = "DEGRADED"
       /\ UNCHANGED <<distrust_level, timer>>

    (* Emergency halt: distrust fully saturated while active *)
    \/ /\ state = "ACTIVE"
       /\ distrust_level = 4
       /\ state' = "HALT"
       /\ UNCHANGED <<distrust_level, timer>>

    (* Fast-Path Halt: Distrust saturates completely while already degraded *)
    \/ /\ state = "DEGRADED"
       /\ distrust_level = 4
       /\ state' = "HALT"
       /\ UNCHANGED <<distrust_level, timer>>

    (* Degraded mode: MaxDegradedTime-step countdown to forced halt *)
    \/ /\ state = "DEGRADED"
       /\ distrust_level < 4   \* Only counts down if distrust is below terminal threshold
       /\ timer < MaxDegradedTime
       /\ timer' = timer + 1
       /\ UNCHANGED <<state, distrust_level>>

    (* Degraded timeout -> Halt *)
    \/ /\ state = "DEGRADED"
       /\ timer >= MaxDegradedTime
       /\ state' = "HALT"
       /\ UNCHANGED <<distrust_level, timer>>

    (* Halt is terminal *)
    \/ /\ state = "HALT"
       /\ UNCHANGED <<state, distrust_level, timer>>

(* Formal specification *)
Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

(* =============================================================================
 * VERIFIKASJONS-INVARIANTER & EGENSKAPER
 * ============================================================================= *)

TypeInvariant ==
    /\ state \in States
    /\ distrust_level \in DistrustLevels
    /\ timer \in 0..MaxDegradedTime

SafetyInvariant ==
    state = "HALT" => (timer >= MaxDegradedTime \/ distrust_level >= 4)

HaltIsTerminal ==
    [][state = "HALT" => UNCHANGED vars]_vars

EventualHalt ==
    (state = "DEGRADED") ~> (state = "HALT")

====
