# Muse Glimmer local model profile

Status: adopted
Owner repo: nsolland/valo-factory
Canonical contract: `valo.openai-compatible.chat.v1`
Profile: `config/muse-glimmer-local-model.json`

## Role

Muse Glimmer 30B is a replaceable local inference worker in the Factory model pool. It is not a new VALO architecture layer.

The adopted artifact is `unsloth/Muse-Glimmer-30B-GGUF`, defaulting to the `UD-Q4_K_XL` GGUF profile for local deployment. The source model card documents text+image input, tool use, multi-step agentic work, failure recovery, 131k+ context and Apache-2.0 licensing.

## Runtime

Preferred local path:

```bash
llama serve -hf unsloth/Muse-Glimmer-30B-GGUF:UD-Q4_K_XL

export VALO_MODEL_ENDPOINT=http://127.0.0.1:8080/v1
export VALO_MODEL_BEARER_TOKEN=
export VALO_MODEL_ID=unsloth/Muse-Glimmer-30B-GGUF:UD-Q4_K_XL
```

`bin/valo-model-provider` consumes the same provider-neutral OpenAI-compatible contract used for hosted models. Swapping Muse Glimmer for another conformant model must remain configuration-only.

## Hermes Agent

Hermes is an optional agent harness, not an authority layer:

```bash
hermes config set model.provider custom
hermes config set model.base_url http://127.0.0.1:8080/v1
hermes config set model.default unsloth/Muse-Glimmer-30B-GGUF:UD-Q4_K_XL
```

Hermes may orchestrate reasoning and tool proposals. It does not widen scope, create mandate or authorize execution.

## Execution boundary

Canonical consequence-bearing path:

`Muse Glimmer -> Hermes (optional) -> tool/action proposal -> VAIG -> reht -> gateway -> Veritas`

Rules:

- Muse Glimmer owns cognition only.
- Hermes owns optional orchestration only.
- VAIG evaluates the proposed action and evidence.
- reht remains the sole final authorization boundary immediately before execution.
- the gateway enforces the permit/deny result mechanically.
- Veritas records what actually happened.
- model output, tool-call syntax, confidence or successful task completion never constitute authority.

## Admission

Before production use, the selected artifact/runtime combination must pass the existing provider-neutral conformance contract and workload-specific evaluation. A model or quantization change is a provider-profile change, not a governance-code change.

## Source

Model card: https://huggingface.co/unsloth/Muse-Glimmer-30B-GGUF
