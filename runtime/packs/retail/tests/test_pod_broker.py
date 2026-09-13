from valo_retail_pack.pod_broker import PODBroker, ProductReceipt, ProductSpec


class FakeProvider:
    def __init__(self):
        self.created = None
        self.published = None

    def create_product(self, spec: ProductSpec) -> ProductReceipt:
        self.created = spec
        return ProductReceipt("fake", "p-1", False, "s-1")

    def publish_product(self, provider_product_id: str) -> ProductReceipt:
        self.published = provider_product_id
        return ProductReceipt("fake", provider_product_id, True, "s-1")


def test_create_and_publish():
    provider = FakeProvider()
    broker = PODBroker(provider)
    spec = ProductSpec(
        title="AI INFLUENCED",
        blueprint_id=1,
        print_provider_id=2,
        variant_ids=(10, 11),
        artwork_url="https://cdn.example.com/design.png",
        retail_price_cents=2900,
    )

    receipt = broker.create_and_publish(spec)

    assert provider.created == spec
    assert provider.published == "p-1"
    assert receipt.published is True
    assert receipt.provider_product_id == "p-1"
