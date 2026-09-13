"""Deterministic continuity evaluation for Digital DNA."""

from __future__ import annotations

from typing import Any, Mapping

from .core import (
    ContinuityDecision,
    DigitalDNAManifest,
    EquivalenceRule,
    Evaluation,
    IdentityTransition,
    MemoryStatus,
    MISSING,
    PairOperator,
    StateOperator,
    StateRule,
    get_path,
)


def _eval_state_rule(state: Mapping[str, Any], rule: StateRule) -> bool | None:
    actual = get_path(state, rule.path)

    if rule.operator is StateOperator.EXISTS:
        return actual is not MISSING
    if actual is MISSING:
        return None

    try:
        if rule.operator is StateOperator.EQUAL:
            return actual == rule.expected
        if rule.operator is StateOperator.NOT_EQUAL:
            return actual != rule.expected
        if rule.operator is StateOperator.IN:
            return actual in rule.expected
        if rule.operator is StateOperator.LTE:
            return actual <= rule.expected
        if rule.operator is StateOperator.GTE:
            return actual >= rule.expected
    except (TypeError, ValueError):
        return None

    raise ValueError(f"unsupported state operator: {rule.operator}")


def _eval_pair_rule(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    rule: EquivalenceRule,
) -> bool | None:
    left = get_path(before, rule.path)
    right = get_path(after, rule.path)

    if left is MISSING or right is MISSING:
        return None

    if rule.operator is PairOperator.EQUAL:
        return left == right

    if rule.operator is PairOperator.NUMERIC_DELTA_LTE:
        if rule.tolerance is None:
            return None
        try:
            return abs(float(right) - float(left)) <= rule.tolerance
        except (TypeError, ValueError):
            return None

    raise ValueError(f"unsupported pair operator: {rule.operator}")


class ContinuityEvaluator:
    """Evaluate identity continuity without granting execution authority."""

    def evaluate(
        self,
        manifest: DigitalDNAManifest,
        transition: IdentityTransition,
    ) -> Evaluation:
        reasons: list[str] = []
        indeterminate = False

        if transition.transformation not in manifest.allowed_transformations:
            reasons.append(f"transformation_not_allowed:{transition.transformation}")
            return self._result(ContinuityDecision.BREAK, reasons, manifest, transition)

        if transition.proposes_protected_amendment:
            if not transition.proposed_manifest_digest:
                reasons.append("protected_amendment_missing_manifest_digest")
                indeterminate = True
            elif transition.amendment_authority is None:
                reasons.append("protected_amendment_requires_authority")
                return self._result(
                    ContinuityDecision.REVIEW_REQUIRED, reasons, manifest, transition
                )
            elif transition.amendment_authority not in manifest.authorized_amenders:
                reasons.append(f"unauthorized_amender:{transition.amendment_authority}")
                return self._result(
                    ContinuityDecision.BREAK, reasons, manifest, transition
                )
            else:
                reasons.append(
                    f"protected_amendment_authorized:{transition.amendment_authority}"
                )

        for path in manifest.required_state_paths:
            if get_path(transition.before_state, path) is MISSING:
                reasons.append(f"required_path_missing_before:{path}")
                indeterminate = True
            if get_path(transition.after_state, path) is MISSING:
                reasons.append(f"required_path_missing_after:{path}")
                indeterminate = True

        seen_memory_ids: set[str] = set()
        for record in transition.memory_records:
            if record.memory_id in seen_memory_ids:
                reasons.append(f"duplicate_memory_id:{record.memory_id}")
                return self._result(
                    ContinuityDecision.BREAK, reasons, manifest, transition
                )
            seen_memory_ids.add(record.memory_id)

            if not record.memory_id or not record.content_digest:
                reasons.append("memory_record_incomplete")
                indeterminate = True

            if record.status in {MemoryStatus.SUPERSEDED, MemoryStatus.REVOKED}:
                if not record.predecessor_ids:
                    reasons.append(
                        f"memory_lineage_missing:{record.memory_id}:{record.status.value}"
                    )
                    indeterminate = True

        for rule in manifest.invariants:
            result = _eval_state_rule(transition.after_state, rule)
            if result is False:
                reasons.append(f"invariant_failed:{rule.path}:{rule.operator.value}")
                return self._result(
                    ContinuityDecision.BREAK, reasons, manifest, transition
                )
            if result is None:
                reasons.append(
                    f"invariant_indeterminate:{rule.path}:{rule.operator.value}"
                )
                indeterminate = True

        for rule in manifest.equivalence_rules:
            result = _eval_pair_rule(
                transition.before_state, transition.after_state, rule
            )
            if result is False:
                reasons.append(f"equivalence_failed:{rule.path}:{rule.operator.value}")
                return self._result(
                    ContinuityDecision.BREAK, reasons, manifest, transition
                )
            if result is None:
                reasons.append(
                    f"equivalence_indeterminate:{rule.path}:{rule.operator.value}"
                )
                indeterminate = True

        for rule in manifest.collapse_conditions:
            result = _eval_state_rule(transition.after_state, rule)
            if result is True:
                reasons.append(
                    f"collapse_condition_met:{rule.path}:{rule.operator.value}"
                )
                return self._result(
                    ContinuityDecision.BREAK, reasons, manifest, transition
                )
            if result is None:
                reasons.append(
                    f"collapse_condition_indeterminate:{rule.path}:{rule.operator.value}"
                )
                indeterminate = True

        if indeterminate:
            return self._result(
                ContinuityDecision.INDETERMINATE, reasons, manifest, transition
            )

        if not reasons:
            reasons.append("all_continuity_constraints_satisfied")

        return self._result(
            ContinuityDecision.CONTINUES, reasons, manifest, transition
        )

    @staticmethod
    def _result(
        decision: ContinuityDecision,
        reasons: list[str],
        manifest: DigitalDNAManifest,
        transition: IdentityTransition,
    ) -> Evaluation:
        return Evaluation(
            decision=decision,
            reasons=tuple(reasons),
            manifest_digest=manifest.manifest_digest(),
            transition_digest=transition.transition_digest(),
        )
