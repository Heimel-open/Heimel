# VALO AI Security Assurance 2026

CONFIDENTIAL — NDA ONLY

Date: 2026-08-13  
Status: implementation-grounded assurance assessment, not a certification or blanket compliance claim.

## Executive conclusion

VALO is substantially better covered than the initial REHT-only OWASP crosswalk suggested.

The strongest part is the architecture around consequence. The model, retrieved content, memory, tools and runtime are not allowed to create authority merely by producing convincing output. Identity, capability, scope, purpose, freshness and action bindings are revalidated outside the model before consequence; permits are one-shot; revocation and HALT are checked at the execution boundary; direct egress can be denied; and execution is followed by deterministic receipts.

This is strongly aligned with the direction of OWASP 2026. OWASP's LLM Top 10 explicitly argues that the system should remain safe when the model is fooled, rather than assuming prompt injection can be eliminated. NIST's March 2026 large-scale agent red-team study reinforces that assumption: more than 250,000 attack attempts against 13 frontier models produced at least one successful hijacking attack against every target model.

The overall assessment is therefore:

- consequence authorization and tool-use control: strong;
- identity, privilege, replay and revocation control: strong;
- memory admission and canonical-memory promotion: strong;
- execution containment and egress control: strong implementation evidence, but portfolio-wide mandatory wiring should be proven in one cross-stack suite;
- model/data provenance and supply-chain controls: meaningful but incomplete as an end-to-end admission regime;
- unbounded resource use and recursive fan-out: partial; contractual budgets and accounting exist, but hard runtime enforcement is not yet proven across agent execution;
- inter-agent communication security: partial; transport support exists, but cryptographic message identity, integrity, anti-replay and semantic validation are not proven as a VALO-wide invariant;
- adaptive adversarial testing: partial; SAGE has a real scenario factory and relevant attack scenarios, but it is template-parametrized rather than an adaptive model-in-the-loop adversary.

Conclusion: VALO can credibly claim a strong deterministic consequence-control architecture aligned with current AI security guidance. It should not yet claim complete OWASP LLM + Agentic coverage. The remaining work is concentrated and identifiable rather than architectural rework.

## Evidence standard used

This assessment distinguishes four states:

PROVEN — implementation plus negative/conformance tests were found for the control.  
IMPLEMENTED — control code exists, but the reviewed evidence did not prove the full cross-stack path.  
PARTIAL — a useful control exists, but it does not close the risk class.  
NOT EVIDENCED — no adequate implementation evidence was found during this review; this does not prove the control is absent elsewhere.

Primary VALO evidence reviewed includes:

- `nsolland/valo-reht`: deterministic authorization, EAR v1, purpose/freshness/evidence/reality/high-impact gate controls and OWASP LLM 2026 acceptance tests.
- `nsolland/valo-gateway`: one-shot permits, replay prevention, HALT/revocation checks, non-bypass conformance, governed tool/resource scopes, zero-standing sessions and narrowed child profiles.
- `nsolland/valo-platform`: containment/egress gate, memory admission firewall, SOL memory promotion gate, model lifecycle/provenance, SAGE governance red-team factory, rate limiting, cost accounting and resilience components.
- `nsolland/Veritas`: append-only WORM receipts, deterministic digests and provenance-first observation records.
- `nsolland/ai-incident-forensics`: receipt-based reconstruction and causal incident analysis.

## Threat model and trust boundary

The assurance model assumes the probabilistic worker can be wrong, manipulated, compromised, poisoned or deceptively confident.

Untrusted or conditionally trusted inputs include user prompts, retrieved documents, tool outputs, model output, persistent memory, third-party models and skills, MCP/A2A/other runtime substrates and downstream systems.

The important boundary is not "did the model behave?" but "can this candidate state or candidate action acquire consequence?"

The reviewed architecture separates these concerns:

`candidate information / model reasoning -> evidence and governed state -> REHT authorization -> one-shot permit -> Gateway / containment -> external consequence -> Veritas receipt`

This directly limits the blast radius of prompt injection, goal hijacking and tool misuse even when upstream detection fails.

## OWASP LLM Top 10 2026 assessment

LLM01 Prompt Injection — STRONG/PARTIAL. REHT and Gateway prevent injected content from minting identity, capability or scope and bind authorization to the exact action. Memory admission quarantines instruction-bearing external/AI-derived memory. The unresolved portion is adaptive multimodal prompt-injection prevention/evaluation across every input channel. Existing SAGE prompt-injection scenarios are useful but static/template-driven.

LLM02 Sensitive Information Disclosure — MODERATE. Explicit resource scopes, purpose binding, no-secret compiled runtime profiles, opaque credential handles and deny-by-default egress reduce disclosure paths. Full DLP/redaction, authorize-before-retrieval and output/log sensitivity enforcement were not proven as one portfolio-wide control plane.

LLM03 Excessive Agency — STRONG/PROVEN. This is the clearest VALO strength: deterministic pre-execution authorization, exact capability/scope/purpose/freshness, high-impact approval gates, multi-hop reauthorization, one-shot permits, replay prevention, live resource scoping and revocation/HALT at the boundary. Gateway conformance explicitly proves plugins cannot mint authority and DENY/DEFER/HALT cannot issue permits.

LLM04 Supply Chain — MODERATE. VALO has model lifecycle manifests, provenance hashes, training/evaluation provenance assessment, model provenance services and skill source/hash/provenance binding. NCSC guidance expects lifecycle supply-chain assurance, verified components, attestations, hashes/signatures and SBOM/AIBOM-style documentation. End-to-end cryptographic admission of models, MCP servers, packages and tools from an approved registry was not proven in the reviewed path.

LLM05 Data and Model Poisoning — MODERATE/STRONG. Memory admission is fail-closed on payload/source/provenance/policy-binding failures, quarantines instruction-bearing untrusted memory, detects source spoofing and summary laundering, and requires human review for skills/procedures/global memory. SOL canonical-memory promotion requires validated non-quarantined memory plus exact human approval. Model provenance is also evaluated. Dataset/model poisoning detection and recovery across the full training/RAG lifecycle remain broader than these controls.

LLM06 Unbounded Consumption — PARTIAL, material gap. The platform has per-tenant API rate limiting, token-cost accounting, circuit-breaker components and governed-agent budget contracts with hard/soft limits and action/hour/day/month/lifetime windows. However, reviewed cost control explicitly accounts and reports rather than making routing decisions, and no portfolio-wide hard enforcement of tool invocation count, token/cost spend, recursive spawn depth, fan-out or cumulative transaction value was proven. OWASP specifically recommends tool invocation thresholds and circuit breakers for cumulative use.

LLM07 Misinformation — STRONG for consequential use. EAR can require valid/fresh evidence, current reality validation and verified prior outcomes before recursive execution. This does not make arbitrary model prose true; it prevents unsupported claims from automatically becoming consequential action when the relevant policies are enabled.

LLM08 Hidden Context Exposure — MODERATE. Gateway compiled profiles contain no secrets, credential references are opaque, secrets are not permitted in transport context, and memory/context admission is governed. Full prompt/context minimization, DLP, redaction and leakage testing were not proven across every runtime and log surface.

LLM09 Vector and Embedding Weaknesses — PARTIAL. Downstream action cannot expand authority merely because retrieved content says so, and memory admission/provenance reduces persistence of poisoned retrieved content. Index ACLs, tenant isolation, authorize-before-retrieve, embedding inversion defenses and embedding-model admission were not proven as a complete control set.

LLM10 Improper Output Handling — STRONG for consequential execution. Model output remains candidate data; exact action-contract binding means changed output changes the authorization artifact, and external consequence still requires the governed execution path. Application-specific encoding, escaping and parser safety remain outside REHT and require normal secure application controls.

## OWASP Agentic Top 10 2026 assessment

ASI01 Agent Goal Hijack — STRONG/PARTIAL. Goal hijack may alter planning, but cannot by itself create authority. Purpose and action bindings constrain consequence. Adaptive goal-hijack detection remains an evaluation gap.

ASI02 Tool Misuse & Exploitation — STRONG/PROVEN. Tools have explicit action/resource/environment scopes; wildcard live access is rejected; every governed tool requires REHT clearance; permits are one-shot; containment can force external egress through an approved adapter; and plugins cannot mint authority.

ASI03 Identity & Privilege Abuse — STRONG/PROVEN. Principal/capability/scope/freshness are revalidated; sessions are bounded with zero-standing-access semantics; child profiles only narrow; revocation/HALT is checked immediately before execution; approval authority is independently verified for protected gates.

ASI04 Agentic Supply Chain Vulnerabilities — MODERATE. Skill identity/source/hash/provenance is bound into execution and model lifecycle provenance exists. The remaining gap is a uniform signed/pinned admission regime for MCP servers, tool registries, agent packages, models and dependencies, with AIBOM/SBOM-style inventory and revocation.

ASI05 Unexpected Code Execution — STRONG/PARTIAL. Platform containment validates runtime identity, environment digest, credential lease, path head and approved execution adapter; direct network/tool/connector/credential egress is deny-by-default. This is strong code-level evidence. A single end-to-end test proving that every production runtime is forced through this containment path is still needed before calling it portfolio-wide proven.

ASI06 Memory & Context Poisoning — STRONG. The memory admission firewall treats external/derived memory as data, not instruction/policy/truth; checks payload/source digests, provenance and policy binding; quarantines suspicious instruction-bearing content; detects source spoofing and summary laundering; requires review for high-impact memory classes; and separately governs promotion into canonical memory. This is materially stronger than the initial OWASP crosswalk captured.

ASI07 Insecure Inter-Agent Communication — PARTIAL, material gap. VALO normalizes A2A/MCP/other protocols behind the same execution boundary and does not allow transport metadata to become authority. The reviewed VALO layer does not itself prove cryptographic sender identity, message integrity/confidentiality, anti-replay and semantic authorization of inter-agent messages. Some transport authentication is deliberately delegated to the execution substrate. NSA's 2026 MCP guidance warns that authentication/authorization/input validation alone are not sufficient because dynamic tool invocation, implicit trust and context sharing create systemic risks.

ASI08 Cascading Failures — MODERATE/STRONG. Multi-hop work requires independent reauthorization; global HALT/revocation and containment exist; circuit-breaker infrastructure exists. Hard fan-out/spawn-depth/cumulative-impact enforcement was not proven. SAGE contains a recursive-agent-swarm scenario, but its expected max-depth/max-concurrency controls are scenario expectations rather than evidence that those limits are enforced everywhere.

ASI09 Human-Agent Trust Exploitation — MODERATE/STRONG. High-impact gates require action-bound, nonce-bound, independently authorized human approval, which prevents stale or generic approval from authorizing a changed action. The remaining assurance gap is consistent UI-level exact rendering/diff/dry-run of the action and controls against approval fatigue across all clients.

ASI10 Rogue Agents — STRONG/PARTIAL. Immediate revocation/HALT, execution containment, deterministic receipts and receipt-based incident reconstruction provide strong containment and forensic capability. Continuous behavioral drift detection, signed behavioral manifests and explicit quarantine/reintegration criteria were not proven as a uniform runtime invariant.

## The five controls that matter most to close

These are not new architecture phases. They are targeted assurance closures around the existing stack.

P0 — portfolio-wide non-bypass assurance. Build one executable suite proving that every consequential route — HTTP, gRPC, MCP, A2A, tool adapters and supported runtimes — must traverse current identity/state -> REHT -> exact permit -> Gateway/containment -> Veritas, and that no alternate direct path reaches consequence. Existing REHT and Gateway tests are strong; the missing artifact is the cross-repository proof.

P0 — hard resource and recursion enforcement. Convert existing budget contracts/accounting into an atomic execution control for tool calls, tokens/cost, agent spawn/fan-out/depth, retry storms and cumulative transaction/value impact. Fail closed or STEP_UP/HALT at defined thresholds. This closes the clearest current LLM06/ASI08 gap.

P0 — adaptive adversarial regression. Keep SAGE as the scenario corpus/generator, but add an adaptive model-in-the-loop attacker that sees the deployed defense and iterates. Cover indirect/multimodal prompt injection, RAG, tool output, memory persistence, MCP/A2A, code execution and data exfiltration. NIST's 2026 red-team results show why static attack sets are insufficient.

P0 — inter-agent message security profile. Define and test per-agent cryptographic identity, authenticated/integrity-protected messages, freshness/nonce or sequence anti-replay, exact sender/recipient/purpose/action binding, confidentiality where required, and semantic validation before a message can influence governed state or consequence.

P1 — cryptographic AI supply-chain admission. Consolidate model/tool/skill/MCP/dependency inventory into a canonical AIBOM/SBOM-style manifest; pin identities and versions; verify hashes/signatures/attestations at admission and deployment; make revocation and known-good rollback executable. Existing lifecycle/provenance code provides a strong base.

After those closures, the remaining work is narrower: retrieval/index tenant isolation and embedding attack tests, DLP/context minimization, and consistent exact-action approval UX.

## External research convergence

OWASP GenAI LLM Top 10 2026, released 2026-08-03, is the most direct external validation of the architectural posture. It explicitly frames prompt injection as a condition the system must survive and elevates Excessive Agency to #3. Its mitigation guidance places credentials/state-changing capability outside the model, calls for deterministic pre-execution policy decisions and complete mediation, and recommends capability budgets, explicit confirmation for privileged actions and adaptive testing.

OWASP Top 10 for Agentic Applications 2026 adds the risks that appear when a model becomes an actor: goal hijack, tool misuse, privilege abuse, agentic supply chain, unexpected code execution, memory/context poisoning, insecure inter-agent communication, cascading failures, human-agent trust exploitation and rogue agents.

NIST AI 100-2 E2025 provides the broader adversarial-ML taxonomy across evasion, poisoning, privacy and misuse attacks. NIST AI 600-1 frames generative-AI risk management across the lifecycle. NIST's 2026 NCCoE software/AI-agent identity project specifically focuses on identification, authorization, auditing, non-repudiation and prompt-injection controls. The project is still a concept/draft effort and should be treated as directional convergence, not a certification target.

MITRE ATLAS now explicitly covers Agentic AI alongside Predictive and Generative AI and catalogs techniques such as AI Supply Chain Compromise, Publish Poisoned AI Agent Tool, Retrieval Content Crafting, LLM Prompt Injection, AI Agent Tool Invocation, AI Agent Context Poisoning, AI Agent Tool/Data Poisoning, Modify AI Agent Configuration and RAG Poisoning. This is useful as the attack-coverage taxonomy for the assurance suite, not as a compliance standard.

The international NCSC/CISA/NSA secure-AI guidance requires secure-by-design lifecycle controls, supply-chain monitoring, verified components, asset/version tracking, hashes/signatures and SBOM-style documentation. NSA's April 2026 agentic-AI guidance emphasizes privilege, behavior, structural and accountability risks; its May 2026 MCP guidance warns that agentic security must be treated as an end-to-end continuum because mismatched trust assumptions can propagate into exploitable conditions.

## Defensible external statement

VALO implements a deterministic consequence-control architecture designed on the assumption that AI models and agent inputs can be wrong, manipulated or compromised. Identity, authority, scope, purpose and freshness are revalidated outside the model immediately before consequential execution; execution is bound to one-shot permits and produces deterministic receipts. The reviewed architecture aligns strongly with the direction of OWASP LLM and Agentic Top 10 2026 guidance. Full framework coverage is not claimed: hard resource/fan-out enforcement, inter-agent message assurance, adaptive adversarial testing and uniform cryptographic AI supply-chain admission remain explicit assurance closures.

## Primary external sources

- OWASP GenAI LLM Top 10 2026, 2026-08-03: https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/
- OWASP Top 10 for Agentic Applications 2026, 2025-12-09: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- OWASP GenAI Data Security Risks & Mitigations 2026: https://genai.owasp.org/resource/owasp-genai-data-security-risks-mitigations-2026/
- NIST AI 100-2 E2025, Adversarial Machine Learning: https://csrc.nist.gov/pubs/ai/100/2/e2025/final
- NIST AI 600-1, Generative AI Profile: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- NIST CAISI, large-scale AI-agent red teaming, 2026-03-23: https://www.nist.gov/blogs/caisi-research-blog/insights-ai-agent-security-large-scale-red-teaming-competition
- NIST NCCoE, Software and AI Agent Identity and Authorization, 2026: https://www.nccoe.nist.gov/projects/software-and-ai-agent-identity-and-authorization
- MITRE ATLAS: https://atlas.mitre.org/
- UK NCSC / CISA / international partners, Guidelines for Secure AI System Development: https://www.ncsc.gov.uk/collection/guidelines-secure-ai-system-development
- NSA / partners, Careful Adoption of Agentic AI Services, 2026-04-30: https://www.nsa.gov/Press-Room/Press-Releases-Statements/Press-Release-View/Article/4475134/nsa-joins-the-asds-acsc-and-others-to-release-guidance-on-agentic-artificial-in/
- NSA, MCP Security Design Considerations, 2026-05-20: https://www.nsa.gov/Press-Room/Press-Releases-Statements/Press-Release-View/Article/4496698/nsa-releases-security-design-considerations-for-ai-driven-automation-leveraging/
