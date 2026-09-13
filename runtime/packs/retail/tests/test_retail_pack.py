from valo_retail_pack import Decision, RetailAction, RetailActionIntentV1, RetailExecutor, RehtPermit


class Adapter:
    def __init__(self, state, ok=True): self.state, self.ok, self.calls = state, ok, 0
    def read_state(self, resource_id): return dict(self.state)
    def execute(self, request):
        from valo_retail_pack.execution import ProviderResult
        self.calls += 1
        if not self.ok: return ProviderResult(False, {"error":"provider"}, None, "provider")
        self.state = {**self.state, **request["after_state"]}
        return ProviderResult(True, {"ok": True}, dict(self.state))


class Veritas:
    def __init__(self): self.rows=[]
    def append(self, payload): self.rows.append(payload); return f"veritas:{len(self.rows)}"


def intent(**kw):
    base=dict(
        tenant_id="t1", action=RetailAction.MOVE_INVENTORY, actor_id="a1", authority_chain=("mgr",),
        purpose="rebalance", jurisdiction="NO", resource_id="sku:1", desired_change={"qty":-2},
        expected_before_state={"version":"7","available":20}, expected_version="7", value_minor=1000,
        currency="NOK", risk_score=.1, valid_until_ns=200, idempotency_key="k1", evidence_refs=("e1",),
        metadata={"available":20,"reserved":2,"safety_stock":5,"requested_qty":2},
    ); base.update(kw); return RetailActionIntentV1(**base)


def permit(i): return RehtPermit(i.tenant_id, i.idempotency_key, {"after_state":{"version":"8","available":18}}, True)


def test_shadow_move_inventory_proves_chain_without_provider_call():
    i=intent(); a=Adapter(i.expected_before_state); v=Veritas(); r=RetailExecutor().execute(intent=i,permit=permit(i),adapter=a,veritas=v,now_ns=100,shadow=True)
    assert r.decision is Decision.ALLOW and r.result=="SHADOW_ONLY" and a.calls==0 and r.veritas_receipt_ref


def test_no_adapter_execution_without_reht_permit():
    i=intent(); a=Adapter(i.expected_before_state); r=RetailExecutor().execute(intent=i,permit=None,adapter=a,veritas=Veritas(),now_ns=100)
    assert r.decision is Decision.DENY and a.calls==0


def test_stale_inventory_rejected():
    i=intent(); a=Adapter({"version":"8","available":19}); r=RetailExecutor().execute(intent=i,permit=permit(i),adapter=a,veritas=Veritas(),now_ns=100)
    assert r.error=="compare-state failed" and a.calls==0


def test_same_idempotency_key_cannot_execute_twice():
    i=intent(); x=RetailExecutor(); a=Adapter(i.expected_before_state); v=Veritas(); p=permit(i)
    r1=x.execute(intent=i,permit=p,adapter=a,veritas=v,now_ns=100); assert r1.result=="EXECUTED"
    i2=intent(expected_before_state={"version":"8","available":18}, expected_version="8")
    r2=x.execute(intent=i2,permit=p,adapter=a,veritas=v,now_ns=100); assert r2.result=="NOT_EXECUTED" and a.calls==1


def test_missing_authority_and_evidence_fail_closed():
    for i in (intent(authority_chain=()), intent(evidence_refs=())):
        r=RetailExecutor().execute(intent=i,permit=permit(i),adapter=Adapter(i.expected_before_state),veritas=Veritas(),now_ns=100)
        assert r.decision is Decision.DENY


def test_high_value_steps_up():
    i=intent(value_minor=100000); r=RetailExecutor().execute(intent=i,permit=permit(i),adapter=Adapter(i.expected_before_state),veritas=Veritas(),now_ns=100)
    assert r.decision is Decision.STEP_UP


def test_provider_error_never_recorded_as_executed():
    i=intent(); r=RetailExecutor().execute(intent=i,permit=permit(i),adapter=Adapter(i.expected_before_state,False),veritas=Veritas(),now_ns=100)
    assert r.result=="NOT_EXECUTED" and r.provider_response_hash


def test_tenant_binding_blocks_cross_tenant_permit():
    i=intent(); p=RehtPermit("other",i.idempotency_key,{"after_state":{}},True); a=Adapter(i.expected_before_state)
    r=RetailExecutor().execute(intent=i,permit=p,adapter=a,veritas=Veritas(),now_ns=100)
    assert r.decision is Decision.DENY and a.calls==0
