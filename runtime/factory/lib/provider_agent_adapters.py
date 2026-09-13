"""Vendor-supported coding-agent runtime adapters for VALO Factory.

The adapters invoke provider CLIs only through documented command surfaces.
They never read credential stores or expose raw tokens. Provider authentication
is capability/entitlement evidence only; authority_effect is always ``none``.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence


class ProviderAgentError(RuntimeError):
    pass


class UnknownProviderAgentError(ProviderAgentError):
    pass


class ProviderAgentUnavailableError(ProviderAgentError):
    pass


class UnsupportedExecutionModeError(ProviderAgentError):
    pass


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class ProviderAgentSpec:
    provider_id: str
    adapter_id: str
    binary: str
    product: str
    login_command: tuple[str, ...]
    headless_login_command: tuple[str, ...] | None
    version_command: tuple[str, ...]
    auth_probe_command: tuple[str, ...] | None
    prompt_transport: str
    documentation_refs: tuple[str, ...]


@dataclass(frozen=True)
class ProviderAgentStatus:
    provider_id: str
    adapter_id: str
    binary: str
    installed: bool
    version: str | None
    auth_state: str
    auth_source: str | None
    entitlement_state: str
    fallback_used: bool | None
    note: str | None
    authority_effect: str = "none"

    def as_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "adapter_id": self.adapter_id,
            "binary": self.binary,
            "installed": self.installed,
            "version": self.version,
            "auth_state": self.auth_state,
            "auth_source": self.auth_source,
            "entitlement_state": self.entitlement_state,
            "fallback_used": self.fallback_used,
            "note": self.note,
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class ExecutionPlan:
    provider_id: str
    adapter_id: str
    execution_mode: str
    prompt_digest: str
    command_surface: tuple[str, ...]
    prompt_transport: str
    authority_effect: str = "none"

    def as_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "adapter_id": self.adapter_id,
            "execution_mode": self.execution_mode,
            "prompt_digest": self.prompt_digest,
            "command_surface": list(self.command_surface),
            "prompt_transport": self.prompt_transport,
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class ExecutionReceipt:
    provider_id: str
    adapter_id: str
    execution_mode: str
    prompt_digest: str
    command_surface: tuple[str, ...]
    started_at_ns: int
    finished_at_ns: int
    exit_status: str
    returncode: int
    stdout_digest: str
    stderr_digest: str
    authority_effect: str = "none"

    def as_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "adapter_id": self.adapter_id,
            "execution_mode": self.execution_mode,
            "prompt_digest": self.prompt_digest,
            "command_surface": list(self.command_surface),
            "started_at_ns": self.started_at_ns,
            "finished_at_ns": self.finished_at_ns,
            "exit_status": self.exit_status,
            "returncode": self.returncode,
            "stdout_digest": self.stdout_digest,
            "stderr_digest": self.stderr_digest,
            "authority_effect": self.authority_effect,
        }


def _spec(
    provider_id: str,
    adapter_id: str,
    binary: str,
    product: str,
    login: Sequence[str],
    *,
    headless_login: Sequence[str] | None = None,
    auth_probe: Sequence[str] | None = None,
    prompt_transport: str = "argument",
    docs: Sequence[str] = (),
) -> ProviderAgentSpec:
    return ProviderAgentSpec(
        provider_id=provider_id,
        adapter_id=adapter_id,
        binary=binary,
        product=product,
        login_command=tuple(login),
        headless_login_command=tuple(headless_login) if headless_login else None,
        version_command=(binary, "--version"),
        auth_probe_command=tuple(auth_probe) if auth_probe else None,
        prompt_transport=prompt_transport,
        documentation_refs=tuple(docs),
    )


PROVIDER_AGENT_SPECS: Mapping[str, ProviderAgentSpec] = {
    "openai_codex": _spec(
        "openai_codex",
        "openai.codex.cli",
        "codex",
        "OpenAI Codex CLI",
        ("codex", "login"),
        headless_login=("codex", "login", "--device-auth"),
        auth_probe=("codex", "login", "status"),
        prompt_transport="stdin",
        docs=(
            "https://learn.chatgpt.com/docs/non-interactive-mode",
            "https://github.com/openai/codex",
        ),
    ),
    "anthropic_claude_code": _spec(
        "anthropic_claude_code",
        "anthropic.claude-code.cli",
        "claude",
        "Anthropic Claude Code",
        ("claude", "login"),
        docs=(
            "https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan",
            "https://support.claude.com/en/articles/14554922-claude-code-user-faq",
        ),
    ),
    "google_antigravity": _spec(
        "google_antigravity",
        "google.antigravity.cli",
        "agy",
        "Google Antigravity CLI",
        ("agy",),
        auth_probe=("agy", "models"),
        docs=(
            "https://codelabs.developers.google.com/antigravity-cli-hands-on",
        ),
    ),
    "github_copilot": _spec(
        "github_copilot",
        "github.copilot.cli",
        "copilot",
        "GitHub Copilot CLI",
        ("copilot", "login"),
        prompt_transport="stdin",
        docs=(
            "https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference",
            "https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference",
        ),
    ),
}


def provider_ids() -> tuple[str, ...]:
    return tuple(PROVIDER_AGENT_SPECS)


def get_spec(provider_id: str) -> ProviderAgentSpec:
    try:
        return PROVIDER_AGENT_SPECS[provider_id]
    except KeyError as exc:
        raise UnknownProviderAgentError(provider_id) from exc


def _digest(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _default_runner(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
    timeout: float | None = None,
) -> CommandResult:
    proc = subprocess.run(
        list(argv),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(proc.returncode, proc.stdout, proc.stderr)


def _safe_version(result: CommandResult) -> str | None:
    if result.returncode != 0:
        return None
    line = (result.stdout or result.stderr).strip().splitlines()
    return line[0][:200] if line else None


def status(
    provider_id: str,
    *,
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., CommandResult] = _default_runner,
) -> ProviderAgentStatus:
    spec = get_spec(provider_id)
    env = dict(os.environ if environ is None else environ)
    installed = which(spec.binary) is not None
    if not installed:
        return ProviderAgentStatus(
            provider_id=spec.provider_id,
            adapter_id=spec.adapter_id,
            binary=spec.binary,
            installed=False,
            version=None,
            auth_state="unavailable",
            auth_source=None,
            entitlement_state="unavailable",
            fallback_used=None,
            note="provider CLI is not installed",
        )

    version = _safe_version(runner(spec.version_command, env=env, timeout=10))

    if provider_id == "openai_codex":
        probe = runner(spec.auth_probe_command, env=env, timeout=15)
        text = (probe.stdout + "\n" + probe.stderr).lower()
        if probe.returncode == 0 and "logged in using chatgpt" in text:
            auth_state, source, ent, fallback, note = (
                "active", "chatgpt_account", "active", False, None
            )
        elif probe.returncode == 0 and "api key" in text:
            auth_state, source, ent, fallback, note = (
                "active", "openai_api", "active", True, None
            )
        else:
            auth_state, source, ent, fallback, note = (
                "unavailable", None, "unavailable", None,
                "run the supported Codex login flow",
            )
    elif provider_id == "anthropic_claude_code":
        if env.get("ANTHROPIC_API_KEY"):
            auth_state, source, ent, fallback, note = (
                "active", "anthropic_api", "active", True,
                "ANTHROPIC_API_KEY is set and takes precedence over subscription login",
            )
        else:
            auth_state, source, ent, fallback, note = (
                "unknown", "claude_account", "unknown", False,
                "Claude Code exposes subscription/account status interactively; "
                "the adapter does not consume a model call merely to probe auth",
            )
    elif provider_id == "google_antigravity":
        probe = runner(spec.auth_probe_command, env=env, timeout=20)
        if probe.returncode == 0:
            auth_state, source, ent, fallback, note = (
                "active", None, "unknown", None,
                "Antigravity is authenticated; CLI output does not safely identify "
                "whether the active supported source is Google OAuth or Google Cloud",
            )
        else:
            auth_state, source, ent, fallback, note = (
                "unavailable", None, "unavailable", None,
                "launch agy and choose a provider-supported login method",
            )
    else:  # github_copilot
        token_vars = [
            name for name in ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
            if env.get(name)
        ]
        if token_vars:
            auth_state, source, ent, fallback, note = (
                "active", "github_enterprise", "unknown", True,
                "GitHub token environment is present; Copilot entitlement is verified "
                "by Copilot CLI when a session starts",
            )
        else:
            gh_path = which("gh")
            if gh_path:
                probe = runner(("gh", "auth", "status"), env=env, timeout=15)
            else:
                probe = CommandResult(1)
            if probe.returncode == 0:
                auth_state, source, ent, fallback, note = (
                    "unknown", "github_account_copilot", "unknown", False,
                    "GitHub CLI is authenticated; Copilot CLI verifies license/policy "
                    "when a session starts",
                )
            else:
                auth_state, source, ent, fallback, note = (
                    "unknown", "github_account_copilot", "unknown", False,
                    "run the supported Copilot OAuth device login flow",
                )

    return ProviderAgentStatus(
        provider_id=spec.provider_id,
        adapter_id=spec.adapter_id,
        binary=spec.binary,
        installed=True,
        version=version,
        auth_state=auth_state,
        auth_source=source,
        entitlement_state=ent,
        fallback_used=fallback,
        note=note,
    )


def login_command(provider_id: str, *, headless: bool = False) -> tuple[str, ...]:
    spec = get_spec(provider_id)
    if headless and spec.headless_login_command:
        return spec.headless_login_command
    return spec.login_command


def _fixed_command(provider_id: str, execution_mode: str) -> tuple[str, ...]:
    if execution_mode not in {"read_only", "workspace_write"}:
        raise UnsupportedExecutionModeError(execution_mode)

    if provider_id == "openai_codex":
        sandbox = "read-only" if execution_mode == "read_only" else "workspace-write"
        return (
            "codex", "exec", "--json", "--ephemeral",
            "--sandbox", sandbox, "-",
        )

    if provider_id == "anthropic_claude_code":
        permission_mode = "plan" if execution_mode == "read_only" else "dontAsk"
        return (
            "claude", "-p", "<PROMPT>",
            "--output-format", "stream-json",
            "--verbose", "--bare",
            "--permission-mode", permission_mode,
        )

    if provider_id == "google_antigravity":
        # Antigravity manages workspace trust/permissions itself. We intentionally
        # do not use --dangerously-skip-permissions.
        return ("agy", "-p", "<PROMPT>")

    if provider_id == "github_copilot":
        permissions = (
            "--deny-tool=write,shell"
            if execution_mode == "read_only"
            else "--allow-tool=write,shell"
        )
        return (
            "copilot",
            "--output-format=json", "--no-ask-user", permissions,
        )

    raise UnknownProviderAgentError(provider_id)


def plan_execution(
    provider_id: str,
    prompt: str,
    *,
    execution_mode: str = "workspace_write",
) -> ExecutionPlan:
    spec = get_spec(provider_id)
    if not prompt.strip():
        raise ProviderAgentError("prompt must not be empty")
    return ExecutionPlan(
        provider_id=spec.provider_id,
        adapter_id=spec.adapter_id,
        execution_mode=execution_mode,
        prompt_digest=_digest(prompt),
        command_surface=_fixed_command(provider_id, execution_mode),
        prompt_transport=spec.prompt_transport,
    )


def _runtime_command(plan: ExecutionPlan, prompt: str) -> tuple[tuple[str, ...], str | None]:
    command = list(plan.command_surface)
    input_text = None
    if plan.prompt_transport == "stdin":
        input_text = prompt
    else:
        try:
            index = command.index("<PROMPT>")
        except ValueError as exc:
            raise ProviderAgentError("prompt placeholder missing") from exc
        command[index] = prompt
    return tuple(command), input_text


def run(
    provider_id: str,
    prompt: str,
    *,
    execution_mode: str = "workspace_write",
    cwd: str | None = None,
    environ: Mapping[str, str] | None = None,
    timeout: float | None = None,
    runner: Callable[..., CommandResult] = _default_runner,
) -> tuple[ExecutionReceipt, CommandResult]:
    plan = plan_execution(provider_id, prompt, execution_mode=execution_mode)
    spec = get_spec(provider_id)
    if shutil.which(spec.binary) is None and runner is _default_runner:
        raise ProviderAgentUnavailableError(f"{spec.binary} is not installed")

    command, input_text = _runtime_command(plan, prompt)
    env = dict(os.environ if environ is None else environ)
    started = time.time_ns()
    try:
        result = runner(
            command,
            cwd=cwd,
            env=env,
            input_text=input_text,
            timeout=timeout,
        )
        exit_status = "success" if result.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        finished = time.time_ns()
        receipt = ExecutionReceipt(
            provider_id=plan.provider_id,
            adapter_id=plan.adapter_id,
            execution_mode=plan.execution_mode,
            prompt_digest=plan.prompt_digest,
            command_surface=plan.command_surface,
            started_at_ns=started,
            finished_at_ns=finished,
            exit_status="timeout",
            returncode=124,
            stdout_digest=_digest(""),
            stderr_digest=_digest("timeout"),
        )
        return receipt, CommandResult(124, "", "timeout")

    finished = time.time_ns()
    receipt = ExecutionReceipt(
        provider_id=plan.provider_id,
        adapter_id=plan.adapter_id,
        execution_mode=plan.execution_mode,
        prompt_digest=plan.prompt_digest,
        command_surface=plan.command_surface,
        started_at_ns=started,
        finished_at_ns=finished,
        exit_status=exit_status,
        returncode=result.returncode,
        stdout_digest=_digest(result.stdout),
        stderr_digest=_digest(result.stderr),
    )
    return receipt, result
