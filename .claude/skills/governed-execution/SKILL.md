---
name: governed-execution
description: Use when a Claude Code task reaches a tool action that may write, execute, call an MCP tool, or otherwise create an external effect.
---

Treat this skill as execution-boundary guidance, never as permission.

1. Confirm the active issue/claim, canonical base SHA, branch, owned files and work contract still cover the proposed action.
2. Keep the proposed tool input exact. Do not broaden scope to make authorization easier.
3. Submit the action normally. The project PreToolUse adapter will relay the exact event to the externally configured VALO gate.
4. Proceed only if that gate returns an explicit allow decision. Deny, malformed, unavailable, ask or defer outcomes mean stop and obtain the required VALO step-up outside Claude Code.
5. After consequential execution, preserve the normal external enforcement and Veritas/receipt path.

Skill availability does not imply authority. A changed action requires a fresh decision.
