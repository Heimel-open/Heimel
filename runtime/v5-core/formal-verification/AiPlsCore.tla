----------------------------- MODULE AiPlsCore -----------------------------
EXTENDS Naturals, TLC

CONSTANTS Normal, SafeMode, Halt, Clear, Uncertain, Denied, Invalid

VARIABLES state, clearance, integrityValid, replayFree, permitValid,
          consumptionReserved, executionAllowed, effectApplied,
          receiptProduced, humanReset

vars == <<state, clearance, integrityValid, replayFree, permitValid,
          consumptionReserved, executionAllowed, effectApplied,
          receiptProduced, humanReset>>

Init ==
  /\ state = Normal
  /\ clearance = Clear
  /\ integrityValid = TRUE
  /\ replayFree = TRUE
  /\ permitValid = TRUE
  /\ consumptionReserved = FALSE
  /\ executionAllowed = FALSE
  /\ effectApplied = FALSE
  /\ receiptProduced = FALSE
  /\ humanReset = FALSE

Evaluate ==
  /\ clearance' \in {Clear, Uncertain, Denied, Invalid}
  /\ integrityValid' \in BOOLEAN
  /\ replayFree' \in BOOLEAN
  /\ permitValid' \in BOOLEAN
  /\ state' = IF state = Halt
       THEN Halt
       ELSE IF ~integrityValid' \/ ~replayFree' \/ ~permitValid'
         \/ clearance' \in {Denied, Invalid}
       THEN Halt
       ELSE IF clearance' = Uncertain THEN SafeMode ELSE Normal
  /\ consumptionReserved' =
       (state # Halt /\ clearance' = Clear /\ integrityValid' /\ replayFree' /\ permitValid')
  /\ executionAllowed' = consumptionReserved'
  /\ effectApplied' = executionAllowed'
  /\ receiptProduced' = effectApplied'
  /\ humanReset' = FALSE

HumanReset ==
  /\ state = Halt
  /\ humanReset' = TRUE
  /\ state' = Normal
  /\ executionAllowed' = FALSE
  /\ effectApplied' = FALSE
  /\ consumptionReserved' = FALSE
  /\ receiptProduced' = FALSE
  /\ UNCHANGED <<clearance, integrityValid, replayFree, permitValid>>

Next == Evaluate \/ HumanReset
Spec == Init /\ [][Next]_vars

HaltSticky == state = Halt /\ ~humanReset => state' = Halt
InvalidIntegrityNeverExecutes == ~integrityValid => ~executionAllowed
DeniedNeverExecutes == clearance \in {Denied, Invalid} => ~executionAllowed
ReplayNeverExecutes == ~replayFree => ~executionAllowed
ExpiredNeverExecutes == ~permitValid => ~executionAllowed
ExecutionRequiresReservation == executionAllowed => consumptionReserved
EffectRequiresReceipt == effectApplied => receiptProduced
=============================================================================
