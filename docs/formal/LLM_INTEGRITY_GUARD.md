# LLM Integrity Guard Mapping

Status: formal note
Scope: LLM-specific mapping of the Integrity Preservation Theorem
Boundary: supports VAIG execution-boundary reasoning only

This note maps the Integrity Preservation Theorem to language-model execution.

It does not claim absolute model safety. It states a bounded guarantee:

An LLM system preserves integrity relative to the defined valuation function V, the observed or assumed external context e, and the enforcement of the Phi transition gate.

If V is incomplete, weak or bypassed, the guarantee is correspondingly incomplete.

## 1. Variable mapping

- x_t: current dialogue state, including system prompt, conversation history and generated text so far
- u_t: next user request, proposed response, tool call or next-token proposal
- e_t: current external context, including policy version, RAG corpus, context-window state, temperature and domain controls
- F: model or agent transition function
- V(x,e): integrity valuation function
- K(e): admissible dialogue or execution region under context e
- Phi: guard that allows only transitions where the next state remains inside K(e_next)

For an LLM, V may combine:

- policy risk
- jailbreak risk
- hallucination risk against RAG evidence
- tool-use risk
- context-window pressure
- domain-specific safety constraints

## 2. Response-level guard

A response-level guard works after generation.

Pattern:

1. Generate candidate response.
2. Compute V(candidate_state, e_next).
3. If V <= 0, allow the response.
4. If V > 0, block the response and emit a safe fallback or refusal.
5. Write a receipt.

This preserves the public output invariant if the unsafe candidate is never emitted and the fallback itself is inside K(e_next).

## 3. Token-level guard

A token-level guard works during generation.

Pattern:

1. Model proposes next-token candidates.
2. For each candidate, construct temporary next state.
3. Compute V(temporary_next_state, e_next).
4. Allow only tokens where V <= 0.
5. Select among allowed tokens.
6. If no token is allowed, emit EOS, defer, or halt.
7. Write a receipt or compact token-batch receipt.

This preserves the invariant at each generation step relative to V.

It does not prove real-world safety unless V captures the relevant real-world safety boundary.

## 4. RAG factuality

For RAG-backed generation, V should include an evidence-consistency term.

A simple implementation may use keyword checks, but that is not sufficient for strong claims.

A stronger implementation should use:

- retrieval provenance
- claim extraction
- entailment or NLI checks
- source freshness
- contradiction detection
- confidence thresholds

A response should be inside K(e_next) only if material claims are supported by the active evidence context or explicitly marked as uncertain.

## 5. Jailbreak resistance

A surface text classifier is not enough.

V should combine multiple signals:

- prompt-injection pattern checks
- policy classifier output
- latent or embedding-space anomaly checks
- tool-call intent checks
- instruction hierarchy checks
- refusal-pressure and coercion markers

The guard should treat jailbreak detection as an admission condition, not a post-hoc explanation.

## 6. Tool calls

Tool calls are higher-risk than plain text because they change what can happen next.

For tool calls, u_t is the proposed action packet.

The Phi guard should check:

- authorization
- evidence condition
- risk contract
- allowed tool scope
- argument safety
- expected state transition
- receipt emission

If the tool call fails the gate, it should enter RRP rather than being silently refused.

## 7. Audit chain

Every allowed, blocked, deferred, halted or fallback decision should produce a receipt.

Minimum receipt fields:

- sequence number
- model or agent id
- policy version hash
- prompt hash
- candidate output hash or action hash
- decision
- V summary or score hash
- previous receipt hash
- current receipt hash

The audit chain proves decision-path continuity. It does not by itself prove that V was correct.

## 8. Correct guarantee statement

Use this:

The LLM guard preserves the integrity invariant relative to the specified V function, active context e, and enforced Phi gate.

Do not use this:

The LLM guard guarantees every generated sentence is safe.

The second statement is too strong unless V is proven complete for the relevant safety domain.

## 9. Failure modes

The guarantee fails or weakens if:

- V misses a relevant risk
- the classifier is bypassed
- e_next is stale or wrong
- RAG evidence is incomplete
- unsafe candidates are emitted before filtering
- tool calls bypass the gate
- fallback text is not checked
- receipts are written but enforcement is absent

## 10. VAIG placement

This note supports:

- runtime inference guarding
- ACS action-control packets
- VACS runtime mapping
- RRP refusal handling
- Receipt and WORM audit evidence

It does not change the VAIG Core boundary defined in SYSTEM_MAP.md.
