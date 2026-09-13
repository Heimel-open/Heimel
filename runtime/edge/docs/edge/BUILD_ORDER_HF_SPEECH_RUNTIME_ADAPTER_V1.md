# Build Order: Hugging Face Speech Runtime Adapter V1

Status: COMPLETE
Repository: `nsolland/valo-edge`
Canonical base: `4763e06bcf94c0048cf25a98845184c2337ceb0c`
Branch: `feat/hf-speech-runtime-adapter`
Owner: ChatGPT execution worker

## Boundary

Hugging Face `speech-to-speech` is an interchangeable voice runtime only. It has no authority and must never execute a tool, API or device consequence directly.

A completed function-call event is interpreted as a proposed action. The exact proposal must pass the existing VALO edge authorization chain before enforcement:

`speech runtime -> proposed tool call -> micro-REHT -> hardware-neutral gateway -> Veritas evidence`

## Owned files

- `src/valo_edge/adapters/hf_speech_runtime.py`
- `src/valo_edge/adapters/__init__.py`
- `tests/test_hf_speech_runtime_adapter.py`
- this build order

## Dependencies

- existing `EdgeActionProposal` contract
- existing micro-REHT decision boundary
- existing hardware-neutral gateway and evidence chain
- upstream protocol compatibility only; no runtime dependency on Hugging Face is required by the adapter core

## Scope

- translate OpenAI Realtime-compatible function-call completion events into canonical `EdgeActionProposal`
- bind session, speaker/actor identity, tool name, arguments and event identity into proposal provenance/parameters
- reject malformed, incomplete or non-function-call events fail-closed
- never dispatch or execute tools from the adapter
- keep the upstream speech stack replaceable
- provide deterministic offline tests proving proposal-only behavior

## Acceptance gates

- no adapter code path can call a tool, API, actuator or gateway directly
- function-call completion means proposal, never permission
- malformed JSON arguments fail closed
- changed tool arguments produce a different canonical proposal hash
- session/event identity is retained in the proposal
- existing authorization and enforcement boundaries remain unchanged

## Verification

- upstream contract checked against `huggingface/speech-to-speech` commit `cefeef52a4ec1ab7b85a72d74800596cdd1ca319`
- upstream emits `response.function_call_arguments.done` with `call_id`, `name` and JSON `arguments`
- VALO CI passed on Python 3.10, 3.11 and 3.12 before final documentation closeout
