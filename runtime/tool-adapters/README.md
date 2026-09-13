# valo-tool-adapters

Tool adapters implementing `ToolInterface` for GitHub, Gmail, Google Drive, Slack,
Docker, Kubernetes, SSH, MCP, and REST.

Every tool adapter refuses to execute without a valid authorization envelope from REHT.
On REHT DENY decision it refuses execution. On ALLOW decision it executes and returns
a `Result`.
