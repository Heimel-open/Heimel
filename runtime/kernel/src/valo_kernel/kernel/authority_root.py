from __future__ import annotations

from ..contracts.authority_root import AuthorityRootBinding


def seal_authority_root_binding(**values: object) -> AuthorityRootBinding:
    provisional = AuthorityRootBinding(**values)
    return provisional.model_copy(update={"root_digest": provisional.computed_digest})
