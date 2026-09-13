# Commercial provider adapters

Work anchor

- Owner: ChatGPT / orchestrator
- Canonical base: `main@ad13f9c3c8af882c7b2151f46747d52a7253bf49`
- Branch: `feat/commercial-provider-adapters-v1`
- Owned files: `docs/COMMERCIAL_PROVIDER_ADAPTERS.md`, `src/valo_operator/adapters/commercial_channels.py`, `src/valo_operator/adapters/__init__.py`, `tests/test_commercial_channels.py`
- Dependencies: existing `VendorConfig`, `ConfiguredGateway`, `ConfiguredVeritas`, Function Fabric action contracts and the unchanged VAIG -> REHT -> RACS execution boundary

Goal: provider-neutral configuration for commercial notification/payment edges without adding any authorization logic to Operator. SMS, voice, email and payment providers are transport/observation configuration only. Real execution remains impossible without a registered Function and the existing governed runtime path.

## Notification edges

`notification_external_config(channel)` supports `email`, `sms` and `voice`. Each channel reads only environment configuration using the channel prefix:

- `<CHANNEL>_BASE_URL`
- `<CHANNEL>_AUTH` or `<CHANNEL>_AUTH_USER` + `<CHANNEL>_AUTH_SECRET`
- `<CHANNEL>_FROM`
- optional send/state path, id field, status field, success state, content type and idempotency-header overrides

The action contract supplies recipient/message and optional subject. The config maps these into transport data. It does not choose the recipient, compose sales claims or authorize contact.

The existing `messaging_external_config()` remains the direct Twilio-shaped external proof. The new helpers are the generic commissioned-provider surface for the commercial loop.

## Payment edge

`payment_external_config()` uses `PAY_*` environment configuration and maps an already-governed PAY action to customer reference, amount, currency, payment-method reference and description. The provider can be Stripe, a bank-payment adapter, a smart-contract adapter or another commissioned payment surface, provided it exposes a send result plus an independently observable state endpoint.

Payment success is never inferred from HTTP success. `ConfiguredVeritas` must observe the configured provider success state before the effect is verified.

## Boundary

Configuration proves connectivity only. Credentials, endpoints, contact details, accepted POC terms and payment-method references are evidence/data; none grant authority. The registered Function semantics and canonical execution boundary remain unchanged.
