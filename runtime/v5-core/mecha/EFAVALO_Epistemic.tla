---------------------------- MODULE EFAVALO_Epistemic ----------------------------
EXTENDS Integers, Sequences, FiniteSets, TLC

CONSTANTS Alice, Bob, Charlie, H1, H2, K1, K2, K3,
          Acuity, CognitiveLoad, AffectiveBias,
          EyeTracker, KeyboardMonitor, ThermalCam,
          HSRSMax, MaxTime

Operators == {Alice, Bob, Charlie}
Handlings == {H1, H2}
Keys == {K1, K2, K3}
HSRS_Components == {Acuity, CognitiveLoad, AffectiveBias}
TrustedSensors == {EyeTracker, KeyboardMonitor, ThermalCam}

HSRSValue == 0..HSRSMax
Thresholds == (Acuity :> 3) @@ (CognitiveLoad :> 2) @@ (AffectiveBias :> 2)
HSRSFloor == 4
VARIABLES hsrs_component_values, hsrs_result, authorityState, sensorIntegrity,
          redState, machineState, evidenceState, independenceState, key_presence,
          key_holder, auth_request, auth_granted, action_executed, vetoed,
          current_time, handling_status, authorizers

vars == <<hsrs_component_values, hsrs_result, authorityState, sensorIntegrity, redState,
          machineState, evidenceState, independenceState, key_presence, key_holder,
          auth_request, auth_granted, action_executed, vetoed, current_time,
          handling_status, authorizers>>

ComputeHSRSResult(vals) ==
    LET score == vals[Acuity] + vals[CognitiveLoad] + vals[AffectiveBias]
    IN IF score > 7 THEN "FloorViolation"
       ELSE IF \E comp \in HSRS_Components: vals[comp] > Thresholds[comp] THEN "ComponentViolation"
       ELSE "OK"

GetHumanState(op) ==
    CASE hsrs_result[op] = "OK" -> "Capable"
      [] hsrs_result[op] = "ComponentViolation" -> "Borderline"
      [] OTHER -> "Incapable"

Execute(h) ==
    LET op == auth_request[h].requestedBy IN
    /\ handling_status[h] = "pending"
    /\ auth_granted[h] = TRUE
    /\ Cardinality(authorizers[h]) = 2
    /\ \A a \in authorizers[h]: a # op
    /\ machineState[op] = "Ready" /\ evidenceState[op] = "Verified"
    /\ independenceState[op] = "Independent"
    /\ authorityState[op] = "Authorized" /\ redState[op] = FALSE /\ sensorIntegrity[op] = "Clean"
    /\ handling_status' = [handling_status EXCEPT ![h] = "executed"]
    /\ action_executed' = [action_executed EXCEPT ![h] = TRUE]
    /\ UNCHANGED <<hsrs_component_values, hsrs_result, authorityState, sensorIntegrity,
                   redState, machineState, evidenceState, independenceState, key_presence,
                   key_holder, auth_request, auth_granted, vetoed, current_time, authorizers>>

Authorize(h) ==
    LET req == auth_request[h].requestedBy IN
    /\ handling_status[h] = "pending"
    /\ current_time - auth_request[h].time <= 5
    /\ \E op1, op2 \in Operators, k1, k2 \in Keys:
          /\ op1 # op2
          /\ op1 # req /\ op2 # req
          /\ k1 # k2
          /\ key_presence[k1] /\ key_presence[k2]
          /\ key_holder[k1] = op1 /\ key_holder[k2] = op2
          /\ auth_granted' = [auth_granted EXCEPT ![h] = TRUE]
          /\ authorizers' = [authorizers EXCEPT ![h] = {op1, op2}]
    /\ UNCHANGED <<hsrs_component_values, hsrs_result, authorityState, sensorIntegrity,
                   redState, machineState, evidenceState, independenceState,
                   key_presence, key_holder, auth_request, action_executed,
                   vetoed, current_time, handling_status>>

RequestAuth(op, h) ==
    /\ handling_status[h] = "pending"
    /\ GetHumanState(op) = "Capable"
    /\ sensorIntegrity[op] = "Clean"
    /\ auth_request' = [auth_request EXCEPT ![h] = [nonce |-> 0, time |-> current_time, requestedBy |-> op]]
    /\ auth_granted' = [auth_granted EXCEPT ![h] = FALSE]
    /\ authorizers' = [authorizers EXCEPT ![h] = {}]
    /\ UNCHANGED <<hsrs_component_values, hsrs_result, authorityState, sensorIntegrity,
                   redState, machineState, evidenceState, independenceState,
                   key_presence, key_holder, action_executed, vetoed, current_time, handling_status>>

Veto(h) ==
    /\ handling_status[h] = "pending"
    /\ handling_status' = [handling_status EXCEPT ![h] = "vetoed"]
    /\ vetoed' = [vetoed EXCEPT ![h] = TRUE]
    /\ auth_granted' = [auth_granted EXCEPT ![h] = FALSE]
    /\ UNCHANGED <<hsrs_component_values, hsrs_result, authorityState, sensorIntegrity,
                   redState, machineState, evidenceState, independenceState,
                   key_presence, key_holder, auth_request, action_executed, current_time, authorizers>>

UpdateHSRS(op, newVals) ==
    /\ sensorIntegrity[op] = "Clean"
    /\ hsrs_component_values' = [hsrs_component_values EXCEPT ![op] = newVals]
    /\ hsrs_result' = [hsrs_result EXCEPT ![op] = ComputeHSRSResult(newVals)]
    /\ UNCHANGED <<authorityState, sensorIntegrity, redState, machineState,
                   evidenceState, independenceState, key_presence, key_holder,
                   auth_request, auth_granted, action_executed, vetoed, current_time, handling_status, authorizers>>

DetectSensorAnomaly(op) ==
    /\ sensorIntegrity[op] = "Clean"
    /\ sensorIntegrity' = [sensorIntegrity EXCEPT ![op] = "Anomaly"]
    /\ redState' = [redState EXCEPT ![op] = TRUE]
    /\ UNCHANGED <<hsrs_component_values, hsrs_result, authorityState, machineState,
                   evidenceState, independenceState, key_presence, key_holder,
                   auth_request, auth_granted, action_executed, vetoed, current_time, handling_status, authorizers>>

Tick ==
    /\ current_time < MaxTime
    /\ current_time' = current_time + 1
    /\ UNCHANGED <<hsrs_component_values, hsrs_result, authorityState, sensorIntegrity,
                   redState, machineState, evidenceState, independenceState,
                   key_presence, key_holder, auth_request, auth_granted,
                   action_executed, vetoed, handling_status, authorizers>>

Next ==
    \/ \E op \in Operators, newVals \in [HSRS_Components -> HSRSValue]: UpdateHSRS(op, newVals)
    \/ \E op \in Operators: DetectSensorAnomaly(op)
    \/ \E op \in Operators, h \in Handlings: RequestAuth(op, h)
    \/ \E h \in Handlings: Authorize(h)
    \/ \E h \in Handlings: Execute(h)
    \/ \E h \in Handlings: Veto(h)
    \/ Tick

Init ==
    /\ hsrs_component_values = [op \in Operators |-> [comp \in HSRS_Components |-> 0]]
    /\ hsrs_result = [op \in Operators |-> "OK"]
    /\ handling_status = [h \in Handlings |-> "pending"]
    /\ authorizers = [h \in Handlings |-> {}]
    /\ authorityState = [op \in Operators |-> "Authorized"]
    /\ sensorIntegrity = [op \in Operators |-> "Clean"]
    /\ redState = [op \in Operators |-> FALSE]
    /\ machineState = [op \in Operators |-> "Ready"]
    /\ evidenceState = [op \in Operators |-> "Verified"]
    /\ independenceState = [op \in Operators |-> "Independent"]
    /\ key_presence = [k \in Keys |-> TRUE]
    /\ key_holder = [k \in Keys |-> IF k = K1 THEN Alice ELSE IF k = K2 THEN Bob ELSE Charlie]
    /\ auth_request = [h \in Handlings |-> [nonce |-> 0, time |-> 0, requestedBy |-> Alice]]
    /\ auth_granted = [h \in Handlings |-> FALSE]
    /\ action_executed = [h \in Handlings |-> FALSE]
    /\ vetoed = [h \in Handlings |-> FALSE]
    /\ current_time = 0

Safety == \A h \in Handlings: action_executed[h] => (Cardinality(authorizers[h]) = 2 /\ \A a \in authorizers[h]: a # auth_request[h].requestedBy)
SeparationOfDuties == \A h \in Handlings: auth_granted[h] => (\A op \in authorizers[h]: op # auth_request[h].requestedBy)
NoDoubleFinalize == \A h \in Handlings: ~(action_executed[h] /\ vetoed[h])

Spec == Init /\ [][Next]_vars /\ (\A h \in Handlings: WF_vars(Authorize(h)) /\ SF_vars(Execute(h)))
=============================================================================
