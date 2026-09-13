from .decision import VACSDecision, VACSStatus
from .schema import AuthorityToken, ExecutionRequest, VerificationResult


class VACSVerifier:
    def verify(self, token: AuthorityToken, request: ExecutionRequest) -> VerificationResult:
        if token.revoked:
            return VerificationResult(False, VACSStatus.REVOKED, VACSDecision.HALT, "authority token revoked", token)

        if token.expired():
            return VerificationResult(False, VACSStatus.EXPIRED, VACSDecision.DENY, "authority token expired", token)

        if token.subject_agent != request.agent_id:
            return VerificationResult(False, VACSStatus.UNAUTHORIZED, VACSDecision.DENY, "agent mismatch", token)

        if token.tenant_id != request.tenant_id:
            return VerificationResult(False, VACSStatus.UNAUTHORIZED, VACSDecision.DENY, "tenant mismatch", token)

        if request.tool not in token.scope.allowed_tools:
            return VerificationResult(False, VACSStatus.UNAUTHORIZED, VACSDecision.DENY, "tool outside delegation scope", token)

        if request.action not in token.scope.allowed_actions:
            return VerificationResult(False, VACSStatus.UNAUTHORIZED, VACSDecision.DENY, "action outside delegation scope", token)

        if request.risk_score > token.scope.max_risk:
            return VerificationResult(False, VACSStatus.ACTIVE, VACSDecision.STEP_UP, "risk exceeds delegated threshold", token)

        if token.scope.max_amount is not None and request.amount is not None:
            if request.amount > token.scope.max_amount:
                return VerificationResult(False, VACSStatus.ACTIVE, VACSDecision.STEP_UP, "amount exceeds delegated limit", token)

        if token.scope.requires_human_over is not None and request.amount is not None:
            if request.amount > token.scope.requires_human_over:
                return VerificationResult(False, VACSStatus.ACTIVE, VACSDecision.DEFER, "human approval required", token)

        return VerificationResult(True, VACSStatus.ACTIVE, VACSDecision.ALLOW, None, token)


def verify(token: AuthorityToken, request: ExecutionRequest) -> VerificationResult:
    return VACSVerifier().verify(token, request)
