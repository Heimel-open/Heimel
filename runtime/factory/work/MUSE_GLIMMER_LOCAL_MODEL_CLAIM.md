# Muse Glimmer local model adoption claim

Status: claimed
Owner: execution worker
Repo: nsolland/valo-factory
Canonical base SHA: 2145de002900d61940567f0ea66d28c1a9b2047d
Branch: feat/muse-glimmer-local-model

Owned files:
- work/MUSE_GLIMMER_LOCAL_MODEL_CLAIM.md
- config/muse-glimmer-local-model.json
- docs/architecture/muse-glimmer-local-model.md
- tests/test_muse_glimmer_local_model.py

Dependencies:
- bin/valo-model-provider / valo.openai-compatible.chat.v1
- Hermes Agent as optional harness
- llama.cpp or another OpenAI-compatible local server
- VAIG evaluation before consequence-bearing execution
- reht as sole final authorization boundary
- gateway enforcement and Veritas receipts

Goal:
Adopt Muse Glimmer 30B as a replaceable local multimodal/agentic model profile in the Factory model pool without granting the model or Hermes any execution authority.
