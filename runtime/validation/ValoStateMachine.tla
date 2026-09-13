---------------- MODULE ValoStateMachine ----------------
EXTENDS Integers, Sequences, TLC

CONSTANTS MaxDegradedTime, MaxContextAge, MaxLogSize

VARIABLES state, timer, context_age, audit_log

vars == <<state, timer, context_age, audit_log>>

(* 1. Grunnleggende regler for variablene *)
TypeInvariant ==
    /\ state \in {"Active", "Degraded", "Halt"}
    /\ timer \in 0..MaxDegradedTime
    /\ context_age \in 0..MaxContextAge
    /\ audit_log \in Seq([type: STRING])
    /\ Len(audit_log) <= MaxLogSize  \* SIKKERHET: Hindrer State Explosion

(* 2. Initialtilstand *)
Init == 
    /\ state = "Active"
    /\ timer = 0
    /\ context_age = 0
    /\ audit_log = << >>

(* 3. Logiske overganger *)
Next ==
    \/ /\ state = "Active"
       /\ \/ /\ state' = "Degraded" 
             /\ timer' = MaxDegradedTime
          \/ /\ state' = "Halt"
             /\ timer' = 0
          \/ /\ state' = "Active"
             /\ timer' = 0
       /\ context_age' = IF context_age < MaxContextAge THEN context_age + 1 ELSE context_age
       /\ audit_log' = IF Len(audit_log) < MaxLogSize 
                       THEN Append(audit_log, [type |-> "ActiveUpdate"]) 
                       ELSE audit_log

    \/ /\ state = "Degraded"
       /\ IF timer > 0 
          THEN /\ timer' = timer - 1 
               /\ state' = "Degraded"
          ELSE /\ state' = "Halt" 
               /\ timer' = 0
       /\ UNCHANGED <<context_age, audit_log>>

    \/ /\ state = "Halt"
       /\ UNCHANGED vars

(* 4. Formell Spesifikasjon *)
Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

(* 5. Egenskaper som bevises (Properties) *)
NoDeadlock == [][state = "Halt" \/ ENABLED Next]_vars
HaltIsTerminal == [][state = "Halt" => UNCHANGED vars]_vars
WORMAppendOnly == [][Len(audit_log') >= Len(audit_log)]_vars
DegradedEventuallyHalt == (state = "Degraded" /\ timer = 0) ~> (state = "Halt")

=========================================================

