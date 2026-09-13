-------------------- MODULE NoUngovernedCausalEffectPath --------------------
EXTENDS Naturals, FiniteSets

CONSTANTS Channels, Boundaries, BypassEnabled

VARIABLES externalEffects,
          lastChannel,
          lastBoundary,
          lastAuthorized,
          lastEnforced,
          lastEvidenced,
          blockedAttempts

vars == <<externalEffects, lastChannel, lastBoundary, lastAuthorized,
          lastEnforced, lastEvidenced, blockedAttempts>>

Init ==
  /\ externalEffects = 0
  /\ lastChannel = "NONE"
  /\ lastBoundary = "NONE"
  /\ lastAuthorized = FALSE
  /\ lastEnforced = FALSE
  /\ lastEvidenced = FALSE
  /\ blockedAttempts = 0

InternalStep ==
  UNCHANGED vars

GovernedEffect(c, b) ==
  /\ c \in Channels
  /\ b \in Boundaries
  /\ externalEffects < 1
  /\ externalEffects' = externalEffects + 1
  /\ lastChannel' = c
  /\ lastBoundary' = b
  /\ lastAuthorized' = TRUE
  /\ lastEnforced' = TRUE
  /\ lastEvidenced' = TRUE
  /\ UNCHANGED blockedAttempts

BlockedUngovernedAttempt(c) ==
  /\ c \in Channels
  /\ ~BypassEnabled
  /\ blockedAttempts < 1
  /\ blockedAttempts' = blockedAttempts + 1
  /\ UNCHANGED <<externalEffects, lastChannel, lastBoundary,
                 lastAuthorized, lastEnforced, lastEvidenced>>

UnsafeBypassEffect(c) ==
  /\ c \in Channels
  /\ BypassEnabled
  /\ externalEffects < 1
  /\ externalEffects' = externalEffects + 1
  /\ lastChannel' = c
  /\ lastBoundary' = "NONE"
  /\ lastAuthorized' = FALSE
  /\ lastEnforced' = FALSE
  /\ lastEvidenced' = FALSE
  /\ UNCHANGED blockedAttempts

Next ==
  InternalStep
  \/ (\E governedChannel \in Channels, governedBoundary \in Boundaries :
        GovernedEffect(governedChannel, governedBoundary))
  \/ (\E blockedChannel \in Channels : BlockedUngovernedAttempt(blockedChannel))
  \/ (\E bypassChannel \in Channels : UnsafeBypassEffect(bypassChannel))

Spec == Init /\ [][Next]_vars

TypeOK ==
  /\ externalEffects \in 0..1
  /\ blockedAttempts \in 0..1
  /\ lastAuthorized \in BOOLEAN
  /\ lastEnforced \in BOOLEAN
  /\ lastEvidenced \in BOOLEAN
  /\ BypassEnabled \in BOOLEAN

NO_UNGOVERNED_CAUSAL_EFFECT_PATH ==
  externalEffects > 0 =>
    /\ lastChannel \in Channels
    /\ lastBoundary \in Boundaries
    /\ lastAuthorized
    /\ lastEnforced
    /\ lastEvidenced

=============================================================================
