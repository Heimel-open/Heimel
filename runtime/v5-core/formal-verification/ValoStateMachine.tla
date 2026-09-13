---------------------------- MODULE ValoStateMachine ----------------------------
EXTENDS Integers, Sequences, TLC

CONSTANTS MaxDegradedTime, MaxContextAge, MaxLogSize

VARIABLES state, timer, context_age, audit_log, clock

vars == <<state, timer, context_age, audit_log, clock>>

TypeInvariant ==
    /\ state \in {"Active", "Degraded", "Halt", "LogFullHalt"}
    /\ timer \in 0..MaxDegradedTime
    /\ context_age \in 0..MaxContextAge
    /\ audit_log \in Seq([type: STRING, from_state: STRING, to_state: STRING,
                          timer_val: Int, timestamp: Int])
    /\ Len(audit_log) <= MaxLogSize
    /\ clock \in Nat

Init ==
    /\ state = "Active"
    /\ timer = 0
    /\ context_age = 0
    /\ audit_log = << >>
    /\ clock = 0

Next ==
    \/ /\ state = "Active"
       /\ Len(audit_log) < MaxLogSize
       /\ \/ /\ state' = "Degraded"
             /\ timer' = MaxDegradedTime
             /\ audit_log' = Append(audit_log,
                    [type |-> "EnterDegraded", from_state |-> "Active", to_state |-> "Degraded",
                     timer_val |-> MaxDegradedTime, timestamp |-> clock+1])
          \/ /\ state' = "Halt"
             /\ timer' = 0
             /\ audit_log' = Append(audit_log,
                    [type |-> "DirectHalt", from_state |-> "Active", to_state |-> "Halt",
                     timer_val |-> 0, timestamp |-> clock+1])
          \/ /\ context_age < MaxContextAge - 1   (* FENCEPOST FIX – prevents overflow *)
             /\ state' = "Active"
             /\ timer' = 0
             /\ audit_log' = Append(audit_log,
                    [type |-> "ActiveUpdate", from_state |-> "Active", to_state |-> "Active",
                     timer_val |-> 0, timestamp |-> clock+1])
       /\ context_age' = context_age + 1   (* guard above ensures context_age < MaxContextAge *)
       /\ clock' = clock + 1

    \/ /\ state = "Degraded"
       /\ Len(audit_log) < MaxLogSize
       /\ IF timer > 0
          THEN /\ timer' = timer - 1
               /\ state' = "Degraded"
               /\ audit_log' = Append(audit_log,
                      [type |-> "DegradedTick", from_state |-> "Degraded", to_state |-> "Degraded",
                       timer_val |-> timer-1, timestamp |-> clock+1])
          ELSE /\ timer' = 0
               /\ state' = "Halt"
               /\ audit_log' = Append(audit_log,
                      [type |-> "TimeoutHalt", from_state |-> "Degraded", to_state |-> "Halt",
                       timer_val |-> 0, timestamp |-> clock+1])
       /\ UNCHANGED <<context_age>>
       /\ clock' = clock + 1

    \/ /\ state = "Halt"
       /\ Len(audit_log) < MaxLogSize
       /\ state' = "Active"
       /\ timer' = 0
       /\ context_age' = 0
       /\ audit_log' = Append(audit_log,
              [type |-> "SystemReset", from_state |-> "Halt", to_state |-> "Active",
               timer_val |-> 0, timestamp |-> clock+1])
       /\ clock' = clock + 1

    \/ /\ state \in {"Active", "Degraded", "Halt"}
       /\ Len(audit_log) = MaxLogSize
       /\ state' = "LogFullHalt"
       /\ UNCHANGED <<timer, context_age, audit_log, clock>>

    \/ /\ state = "LogFullHalt"
       /\ UNCHANGED vars

Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

SafetyInvariant ==
    (state = "Active") => (context_age < MaxContextAge)

WORMAppendOnly == [][Len(audit_log') >= Len(audit_log)]_vars

LogFullHaltIsTerminal ==
    [][state = "LogFullHalt" => UNCHANGED vars]_vars

DegradedEventuallyHalt ==
    (state = "Degraded" /\ timer = 0) ~> (state = "Halt" \/ state = "LogFullHalt")

LogFullReachable ==
    (Len(audit_log) = MaxLogSize) ~> (state = "LogFullHalt")

=============================================================================
