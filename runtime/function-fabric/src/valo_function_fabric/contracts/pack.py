from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .function import FunctionDefinition


class PackRule(BaseModel):
    """A pack-level constraint that can tighten (never weaken) core governance."""

    constraint_type: str
    subject: str
    predicate: str
    severity: str = "REQUIRED"

    model_config = ConfigDict(extra="forbid", frozen=True)


class Pack(BaseModel):
    """Domain extension format. Packs can add domain types, functions, rules
    and mappings. They can NEVER weaken core governance, redefine ISA
    semantics, bypass REHT, or write Kernel state directly."""

    pack: str  # e.g. "trades", "public"
    version: str
    functions: list[FunctionDefinition] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)
    rules: list[PackRule] = Field(default_factory=list)
    mappings: dict[str, str] = Field(default_factory=dict)
    tests: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)
