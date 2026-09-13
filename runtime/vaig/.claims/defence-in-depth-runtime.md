# Claim: defence-in-depth runtime

Owner: OpenAI / active assistant session
Base SHA: 0b96b91e1e97a37c082b50cd16a24a2f2eada944
Branch: feat/defence-in-depth-runtime
Draft PR: #189

Owned files:
- vaig/security_pipeline.py
- vaig/instruments/activation_safety_classifier.py
- vaig/instruments/registry.py
- vaig/instruments/__init__.py
- tests/test_security_pipeline.py
- tests/test_activation_safety_classifier.py

Dependencies:
- existing VAIG instrument registry and attack_pattern_library
- ModelSignalBundle/native signal evidence
- reht remains external sole execution-authorization boundary

Scope: model-security observability and evidence only; no authority or execution enforcement is added to VAIG.
