# CrabTrap governed connector integration

Canonical upstream: `brexhq/CrabTrap@ac871ccc4460249f71cfc8b55ae4ba6130351b74`

The connector targets the verified forwarding boundary in `internal/proxy/handler.go`: native `CheckApproval` runs before `h.client.Do(proxyReq)`, and the upstream response is available immediately after that call.

## Install

Copy or vendor `connectors/crabtrap/governed` into the CrabTrap source tree as `internal/governed`, preserving the package name `governed`.

Configure one client during gateway startup and inject it into `proxy.Handler`:

```go
governedClient := &governed.Client{
    GateURL:     os.Getenv("VALO_EGRESS_GATE_URL"),
    SharedToken: os.Getenv("VALO_EGRESS_SHARED_TOKEN"),
    Identity: governed.Identity{
        MissionID:        os.Getenv("VALO_MISSION_ID"),
        PrincipalID:      os.Getenv("VALO_PRINCIPAL_ID"),
        AuthorityGrantID: os.Getenv("VALO_AUTHORITY_GRANT_ID"),
    },
}
```

All identity fields are required. Missing identity or an unavailable gate blocks traffic.

## Request insertion

In `processRequest`, keep CrabTrap's existing authentication, SSRF checks, body buffering and native approval call. Treat the native result only as transport evidence.

Immediately after `CheckApproval` returns and before the native decision switch can forward:

```go
signals := governed.SignalsFromCrabTrap(
    string(decision.Decision),
    decision.ApprovedBy,
)

snapshot, err := governed.RequestSnapshot(requestID, r, originalRequestBody)
if err != nil {
    return errorResponse(http.StatusForbidden, "text/plain", "Governed request binding failed")
}

gateDecision, err := h.governedClient.Authorize(ctx, snapshot, signals)
if err != nil {
    return errorResponse(http.StatusServiceUnavailable, "text/plain", "Governance unavailable")
}

switch gateDecision.Decision {
case "ALLOW":
    // continue
case "MODIFY":
    // Never forward the original. Return a bounded denial and require the
    // caller to submit the replacement as a new governed request.
    return errorResponse(http.StatusConflict, "text/plain", "Request modification required")
default:
    return errorResponse(http.StatusForbidden, "text/plain", "Governed request denied")
}
```

Do not retain CrabTrap's native `ALLOW` as a separate authorization path. A static `DENY` may stop early, but static `ALLOW`, passthrough and LLM outcomes only populate `TransportSignals`.

After `proxyReq` has been constructed and hop-by-hop headers stripped, immediately before `h.client.Do(proxyReq)`:

```go
if err := governed.VerifyBeforeForward(snapshot, proxyReq, requestBody); err != nil {
    return errorResponse(http.StatusForbidden, "text/plain", "Request changed after authorization")
}
```

For a large request body that CrabTrap cannot fully buffer, governed mode must deny rather than stream an unbound tail. Set the connector request limit to the maximum size allowed for exact byte binding.

## Response insertion

In governed mode, do not use CrabTrap's direct streaming branch. The full response must fit inside `MaxResponseBody` and be inspected before any byte is sent to the agent.

Immediately after `h.client.Do(proxyReq)` succeeds:

```go
responseBody, err := governed.ReadBoundedBody(resp.Body, h.governedClient.MaxResponseBody)
if err != nil {
    return errorResponse(http.StatusBadGateway, "text/plain", "Response cannot be safely inspected")
}

responseDecision, err := h.governedClient.InspectResponse(ctx, snapshot, resp, responseBody)
if err != nil {
    return errorResponse(http.StatusServiceUnavailable, "text/plain", "Response governance unavailable")
}

if err := governed.ApplyResponseDecision(resp, responseBody, responseDecision); err != nil {
    return errorResponse(http.StatusForbidden, "text/plain", "Upstream response denied")
}
```

Continue through CrabTrap's existing response audit and delivery path only after `ApplyResponseDecision` succeeds. The returned body and headers are then the governed representation.

## Required mode changes

- Disable passthrough fallback.
- Deny WebSocket upgrades in governed mode.
- Disable response streaming in governed mode.
- Deny request bodies exceeding the exact-binding limit.
- Deny responses exceeding the inspection limit.
- Preserve CrabTrap SSRF, DNS-rebinding, rate-limit, circuit-breaker, TLS and audit controls.
- Do not log the gate bearer token, raw authorization headers or unredacted secret response material.

## Runtime

```bash
export VALO_EGRESS_GATE_URL=http://127.0.0.1:8082
export VALO_EGRESS_GOVERNANCE_COMMAND=./bin/valo-egress-governance-broker
export VALO_EGRESS_VAIG_COMMAND='<VAIG adapter command>'
export VALO_EGRESS_REHT_COMMAND='<REHT issuer command>'
export VALO_EGRESS_RACS_COMMAND='<RACS decision command>'
export VALO_MISSION_ID='<bounded mission id>'
export VALO_PRINCIPAL_ID='<agent principal id>'
export VALO_AUTHORITY_GRANT_ID='<active grant id>'

./bin/valo-egress-gate --serve --bind 127.0.0.1 --port 8082
```

The transport is ready only when `GET /healthz` returns HTTP 200 and every stage command is configured. Health does not imply authority; each request still requires fresh, digest-bound artifacts.
