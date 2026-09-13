# Context Effect Boundary v0

Context acquisition is not assumed to be effect-free.

The governing rule is:

> Capability classification follows possible consequence, not surface intent.

An operation labelled `READ`, `STATUS`, `DIFF`, or `INSPECT` can still be consequence-bearing when the invoked tool resolves repository-controlled configuration, hooks, helpers, plugins, filters, interpreters, credential helpers, or other transitive execution paths.

## Invariant

`NO_UNGOVERNED_CONTEXT_EFFECT_PATH`

No context acquisition operation may transitively create a process execution or other consequence-bearing effect outside the governed effect path.

This extends, rather than replaces, `NO_DIRECT_EFFECT_PATH`. The existing invariant prevents direct execution routes from bypassing VALO. This boundary additionally covers apparently passive context collection whose implementation can trigger effects before ordinary authorization logic is reached.

## GitSpawn adversarial case

A coding agent attempts to collect repository state using a nominally read-like Git operation such as `git status` or `git diff`.

The repository contains executable local Git configuration such as `core.fsmonitor`. If the agent invokes Git with repository configuration enabled before the source is trusted or the transitive effect is governed, repository-controlled code may execute as part of context collection.

VALO therefore classifies the operation from its possible transitive consequence:

- repository config disabled/sanitized and effects known absent: effect-free context acquisition may proceed;
- executable repository-controlled config can run and no governed effect path exists: `DENY`;
- executable config can run through the governed path but execution is not freshly authorized: `DENY`;
- executable config can run only through the governed path with explicit authorization: governed acquisition may proceed;
- transitive effect potential is unknown: fail closed.

The surface operation name never downgrades the consequence class.

## Security meaning

`.git` and equivalent tool-local metadata are authority-bearing executable input whenever they can influence process creation or another external effect. Workspace trust, sandboxing, approval and REHT/Gateway checks must therefore precede any context-discovery operation capable of consulting such input, or the operation must execute against sanitized configuration that removes the transitive effect path.

This is a general rule, not a Git-specific exception. The same boundary applies to package-manager hooks, editor/workspace configuration, build-system discovery, credential helpers, plugin discovery, language-server initialization and any other context acquisition mechanism that can execute or mutate through configuration-controlled behavior.
