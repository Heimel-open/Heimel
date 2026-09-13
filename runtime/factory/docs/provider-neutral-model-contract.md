# Provider-neutral model contract

Status: implemented
Owner: nsolland
Branch: `feat/provider-neutral-model-contract`
Canonical base: `1d7e9aa9513f28b79843b3279e652367be105b76`
Contract: `valo.openai-compatible.chat.v1`

## Boundary

The model provider is a transport and inference dependency. It does not own role definitions, workflow state, context selection, policy, governance evaluation, authorization or execution.

A provider change is configuration-only:

- `VALO_MODEL_ENDPOINT`
- `VALO_MODEL_BEARER_TOKEN`
- `VALO_MODEL_ID`
- optional `VALO_MODEL_TIMEOUT_SECONDS`

The endpoint must expose the OpenAI-compatible `POST /chat/completions` contract. Commercial, hosted open-model and self-hosted endpoints use the same adapter.

## Adapter

`bin/valo-model-provider`:

1. reads one canonical workflow request;
2. injects only the configured model identifier;
3. sends the request to the configured endpoint;
4. removes provider-specific response extensions;
5. returns a normalized result and provider receipt.

The bearer token is used only in the HTTP Authorization header. It is never included in output, digest input, logs or receipts.

## Receipt

`schemas/model-provider-receipt.schema.json` records:

- contract version;
- endpoint identity without path, query or credentials;
- model identifier;
- canonical request and normalized response digests;
- HTTP status and nanosecond timing.

This receipt proves which provider boundary was used. It does not replace governance clearance, execution receipt or outcome evidence.

## Conformance

`tests/test_model_provider.py` proves offline that:

- the same workflow messages and parameters survive provider swaps;
- only endpoint, token and model configuration vary;
- canonical request bytes are stable;
- provider-specific response fields do not cross the boundary;
- tokens do not enter receipts;
- invalid non-HTTP endpoints are rejected.

CI runs the conformance suite without credentials or network access.

## Live validation

Use the same request file for each endpoint:

```bash
export VALO_MODEL_ENDPOINT=https://provider.example/v1
export VALO_MODEL_BEARER_TOKEN=...
export VALO_MODEL_ID=model-name
bin/valo-model-provider --request request.json
```

For local infrastructure, an empty bearer token is accepted:

```bash
export VALO_MODEL_ENDPOINT=http://127.0.0.1:8000/v1
export VALO_MODEL_BEARER_TOKEN=
export VALO_MODEL_ID=local-model
bin/valo-model-provider --request request.json
```

A live provider is conformant when the adapter returns the same normalized result shape and a valid provider receipt without workflow or governance code changes.
