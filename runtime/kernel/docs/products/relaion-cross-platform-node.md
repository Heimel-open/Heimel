# relAIon Node — Cross-platform contract

relAIon is not a Windows product. Windows, NVIDIA RTX/DGX, Linux and macOS are substrate variants behind one governed node contract.

## Canonical READY contract

A host is a relAIon node only when all are true:

1. Device identity established.
2. Local state protected.
3. At least one verified local inference route operational.
4. Capability registry operational.
5. VALO consequence gate operational.
6. DENY test proves an unauthorized effect cannot reach its provider.
7. Receipt generation operational.
8. Capability grants are reversible.
9. Remote processing is OFF unless explicitly enabled.

No platform adapter may weaken this contract.

## Platform adapters

### Windows / Copilot+
Preferred routes: Foundry Local, Windows ML, App Actions, ODR/MCP.

### NVIDIA
NVIDIA is a compute/provider specialization rather than an operating-system identity. A relAIon NVIDIA node may run on Windows or Linux. Preferred routes are selected from admitted local backends such as TensorRT for RTX, llama.cpp/Ollama, vLLM or other NVIDIA-accelerated local inference. GPU availability never grants authority.

### Linux
Linux adapter owns package/runtime discovery, local inference bootstrap, systemd user service, XDG state/config paths and capability providers. Distribution-specific packaging is outside the kernel; the READY contract is identical.

### macOS
macOS adapter owns Apple Silicon detection, local inference bootstrap and application/service integration. Preferred local inference routes may use MLX/Core AI-compatible implementations. macOS privacy/TCC grants remain user-controlled and are not treated as execution authority.

## Routing rule

Intent -> relAIon -> capability discovery -> normalized effect -> VALO/REHT -> ALLOW/DENY/ESCALATE -> platform/provider adapter -> effect -> receipt.

The model runtime, accelerator and operating system are replaceable capability substrates. Handlingsrett remains invariant.