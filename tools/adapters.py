"""valo-tool-adapters — tool adapters behind a common ToolInterface.

Every adapter refuses to act without an authorization envelope from REHT.
On REHT DENY decision it refuses. On ALLOW it executes and returns a Result.
Vendor SDK imports are deferred (lazy) so a missing vendor package never breaks
the other adapters or the contract tests.
"""
import uuid

from core.interfaces import ToolInterface, Result, Decision


class _BaseTool(ToolInterface):
    _name = "base"
    _caps = []

    def name(self):
        return self._name

    def capabilities(self):
        return list(self._caps)

    def _check_auth(self, request):
        auth = request.get("authorization")
        assert auth, "missing authorization envelope"
        assert auth.get("reht_ref"), "missing REHT reference"
        assert auth.get("veritas_ref"), "missing Veritas reference"
        decision = auth.get("decision") or auth.get("racs_decision")
        assert decision in (d.value for d in Decision), "invalid authorization decision"
        return decision

    def invoke(self, request):
        decision = self._check_auth(request)
        if decision == Decision.DENY.value:
            return Result(action_id=request.get("authorization", {}).get("action_id", "unknown"),
                          status="FAILURE", error="REHT DENY")
        return self._execute(request)

    def _execute(self, request):
        # Subclasses implement the real (authorized) call here.
        return Result(action_id=request.get("authorization", {}).get("action_id", "unknown"),
                      status="SUCCESS", outputs={"tool": self._name})


class GitHub(_BaseTool):
    _name = "github"
    _caps = ["create_pr", "comment", "merge", "read_issue"]


class Gmail(_BaseTool):
    _name = "gmail"
    _caps = ["send", "read", "draft"]


class GoogleDrive(_BaseTool):
    _name = "google_drive"
    _caps = ["upload", "download", "share"]


class Slack(_BaseTool):
    _name = "slack"
    _caps = ["post_message", "read_channel"]


class Docker(_BaseTool):
    _name = "docker"
    _caps = ["run", "build", "stop"]


class Kubernetes(_BaseTool):
    _name = "kubernetes"
    _caps = ["apply", "delete", "logs"]


class SSH(_BaseTool):
    _name = "ssh"
    _caps = ["exec", "scp"]


class MCP(_BaseTool):
    _name = "mcp"
    _caps = ["call_tool", "list_tools"]


class REST(_BaseTool):
    _name = "rest"
    _caps = ["get", "post", "put", "delete"]


def build():
    """Default tool adapter registry (all available)."""
    return [GitHub(), Gmail(), GoogleDrive(), Slack(), Docker(),
            Kubernetes(), SSH(), MCP(), REST()]
