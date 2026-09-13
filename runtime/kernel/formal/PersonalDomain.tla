------------------------------ MODULE PersonalDomain ------------------------------
EXTENDS Naturals, Sequences

CONSTANTS
    Principal,
    Agent,
    Purpose,
    Action,
    Provider,
    Fields,
    Values,
    NoValue,
    InitialValue,
    DelegationExpires,
    DisclosurePolicy,
    EffectField,
    EffectValue,
    MaxClock

InitialState == [f \in Fields |-> InitialValue]

InitialDelegation == [
    active |-> TRUE,
    principal |-> Principal,
    delegate |-> Agent,
    purpose |-> Purpose,
    action |-> Action,
    expires |-> DelegationExpires
]

ASSUME
    /\ Principal \notin {Agent, Provider}
    /\ Agent # Provider
    /\ NoValue \notin Values
    /\ Fields # {}
    /\ InitialValue \in Values
    /\ DelegationExpires \in Nat
    /\ EffectField \in Fields
    /\ EffectValue \in Values
    /\ MaxClock \in Nat
    /\ DisclosurePolicy \subseteq Fields

VARIABLES
    state,
    version,
    clock,
    delegation,
    projection,
    projectionVersion,
    projectionDestination,
    candidate,
    candidateVersion,
    rehtAuthorized,
    phase,
    effectOccurred,
    evidence

vars == <<
    state,
    version,
    clock,
    delegation,
    projection,
    projectionVersion,
    projectionDestination,
    candidate,
    candidateVersion,
    rehtAuthorized,
    phase,
    effectOccurred,
    evidence
>>

Phases == {"READY", "DISCLOSED", "CANDIDATE", "AUTHORIZED", "DONE", "REVOKED"}

EvidenceEvent == [
    kind : {"DISCLOSURE", "REHT", "EFFECT", "REJECT"},
    version : Nat,
    clock : Nat,
    authorityValid : BOOLEAN
]

EmptyProjection == [f \in Fields |-> NoValue]

Project(s) ==
    [f \in Fields |-> IF f \in DisclosurePolicy THEN s[f] ELSE NoValue]

ProjectionIsMinimal(p) ==
    \A f \in Fields :
        \/ f \in DisclosurePolicy
        \/ p[f] = NoValue

ApplyEffect(s) == [s EXCEPT ![EffectField] = EffectValue]

DelegationValid(d, now) ==
    /\ d.active
    /\ d.principal = Principal
    /\ d.delegate = Agent
    /\ d.purpose = Purpose
    /\ d.action = Action
    /\ now <= d.expires

TypeInvariant ==
    /\ state \in [Fields -> Values]
    /\ version \in Nat
    /\ clock \in 0..MaxClock
    /\ delegation \in [
          active : BOOLEAN,
          principal : {Principal},
          delegate : {Agent},
          purpose : {Purpose},
          action : {Action},
          expires : Nat
       ]
    /\ projection \in [Fields -> (Values \cup {NoValue})]
    /\ projectionVersion \in Nat
    /\ projectionDestination \in {Provider, NoValue}
    /\ candidate \in {Action, NoValue}
    /\ candidateVersion \in Nat
    /\ rehtAuthorized \in BOOLEAN
    /\ phase \in Phases
    /\ effectOccurred \in BOOLEAN
    /\ evidence \in Seq(EvidenceEvent)

Init ==
    /\ state = InitialState
    /\ version = 0
    /\ clock = 0
    /\ delegation = InitialDelegation
    /\ projection = EmptyProjection
    /\ projectionVersion = 0
    /\ projectionDestination = NoValue
    /\ candidate = NoValue
    /\ candidateVersion = 0
    /\ rehtAuthorized = FALSE
    /\ phase = "READY"
    /\ effectOccurred = FALSE
    /\ evidence = << >>

Tick ==
    /\ phase \notin {"DONE", "REVOKED"}
    /\ clock < MaxClock
    /\ clock' = clock + 1
    /\ UNCHANGED <<
          state, version, delegation, projection, projectionVersion,
          projectionDestination, candidate, candidateVersion,
          rehtAuthorized, phase, effectOccurred, evidence
       >>

Revoke ==
    /\ phase \notin {"DONE", "REVOKED"}
    /\ delegation.active
    /\ delegation' = [delegation EXCEPT !.active = FALSE]
    /\ rehtAuthorized' = FALSE
    /\ phase' = "REVOKED"
    /\ evidence' = Append(evidence, [
          kind |-> "REJECT",
          version |-> version,
          clock |-> clock,
          authorityValid |-> FALSE
       ])
    /\ UNCHANGED <<
          state, version, clock, projection, projectionVersion,
          projectionDestination, candidate, candidateVersion, effectOccurred
       >>

AuthorizeDisclosure ==
    /\ phase = "READY"
    /\ DelegationValid(delegation, clock)
    /\ projection' = Project(state)
    /\ projectionVersion' = version
    /\ projectionDestination' = Provider
    /\ phase' = "DISCLOSED"
    /\ evidence' = Append(evidence, [
          kind |-> "DISCLOSURE",
          version |-> version,
          clock |-> clock,
          authorityValid |-> TRUE
       ])
    /\ UNCHANGED <<
          state, version, clock, delegation, candidate,
          candidateVersion, rehtAuthorized, effectOccurred
       >>

WorkerCandidate ==
    /\ phase = "DISCLOSED"
    /\ projectionDestination = Provider
    /\ ProjectionIsMinimal(projection)
    /\ projectionVersion = version
    /\ candidate' = Action
    /\ candidateVersion' = version
    /\ rehtAuthorized' = FALSE
    /\ phase' = "CANDIDATE"
    /\ UNCHANGED <<
          state, version, clock, delegation, projection,
          projectionVersion, projectionDestination, effectOccurred, evidence
       >>

FreshRehtAuthorize ==
    /\ phase = "CANDIDATE"
    /\ candidate = Action
    /\ candidateVersion = version
    /\ DelegationValid(delegation, clock)
    /\ rehtAuthorized' = TRUE
    /\ phase' = "AUTHORIZED"
    /\ evidence' = Append(evidence, [
          kind |-> "REHT",
          version |-> version,
          clock |-> clock,
          authorityValid |-> TRUE
       ])
    /\ UNCHANGED <<
          state, version, clock, delegation, projection,
          projectionVersion, projectionDestination,
          candidate, candidateVersion, effectOccurred
       >>

Effect ==
    /\ phase = "AUTHORIZED"
    /\ rehtAuthorized
    /\ candidate = Action
    /\ candidateVersion = version
    /\ DelegationValid(delegation, clock)
    /\ state' = ApplyEffect(state)
    /\ version' = version + 1
    /\ effectOccurred' = TRUE
    /\ rehtAuthorized' = FALSE
    /\ phase' = "DONE"
    /\ evidence' = Append(evidence, [
          kind |-> "EFFECT",
          version |-> version,
          clock |-> clock,
          authorityValid |-> TRUE
       ])
    /\ UNCHANGED <<
          clock, delegation, projection, projectionVersion,
          projectionDestination, candidate, candidateVersion
       >>

TerminalStutter ==
    /\ phase \in {"DONE", "REVOKED"}
    /\ UNCHANGED vars

Next ==
    \/ Tick
    \/ Revoke
    \/ AuthorizeDisclosure
    \/ WorkerCandidate
    \/ FreshRehtAuthorize
    \/ Effect
    \/ TerminalStutter

Spec == Init /\ [][Next]_vars

NoUnauthorizedEffect ==
    effectOccurred => DelegationValid(delegation, clock)

NoEffectAfterRevocation ==
    phase = "REVOKED" => ~effectOccurred

NoDisclosureOvershare ==
    phase \in {"DISCLOSED", "CANDIDATE", "AUTHORIZED"} =>
        ProjectionIsMinimal(projection)

DisclosureBoundToCurrentState ==
    phase \in {"DISCLOSED", "CANDIDATE", "AUTHORIZED"} =>
        projectionVersion = version

NoStaleCandidateAuthorization ==
    phase = "AUTHORIZED" => candidateVersion = version

NoEffectWithoutDisclosure ==
    effectOccurred =>
        \E i \in 1..Len(evidence) : evidence[i].kind = "DISCLOSURE"

NoEffectWithoutFreshReht ==
    effectOccurred =>
        \E i \in 1..Len(evidence) :
            /\ evidence[i].kind = "REHT"
            /\ evidence[i].authorityValid

PrincipalRemainsAuthorityRoot ==
    delegation.principal = Principal

ProviderNeverBecomesAuthority ==
    /\ delegation.principal # Provider
    /\ delegation.delegate # Provider

RecoveryContinuity ==
    state = IF effectOccurred THEN ApplyEffect(InitialState) ELSE InitialState

=============================================================================
