from lib.escrow_providers import EscrowProviderKind, PROVIDERS, mvp_provider, ranked_providers


def test_mvp_provider_is_true_escrow():
    provider = mvp_provider()
    assert provider.name == "Escrow.com"
    assert provider.kind == EscrowProviderKind.TRUE_ESCROW
    assert provider.service_acceptance_supported is True


def test_scale_candidates_are_registered():
    assert {"escrow_com", "adyen", "mangopay", "lemonway"} <= set(PROVIDERS)
    assert [provider.priority for provider in ranked_providers()] == [1, 2, 3, 4]
