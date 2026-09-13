from vacs.src.roi_gate import ROIEstimate, ROIPolicy, VALOROIGate


def main():
    gate = VALOROIGate()
    policy = ROIPolicy(
        min_net_value_usd=0.0,
        min_roi_ratio=1.25,
        max_cost_without_step_up_usd=25.0,
        min_confidence=0.70,
    )

    examples = [
        ROIEstimate(
            action_id="cheap-summary",
            expected_value_usd=8.00,
            estimated_cost_usd=0.40,
            confidence=0.95,
            value_basis="analyst time saved",
            cost_basis="model tokens",
        ),
        ROIEstimate(
            action_id="bulk-low-value-report",
            expected_value_usd=4.00,
            estimated_cost_usd=9.00,
            risk_cost_usd=2.00,
            confidence=0.85,
            value_basis="unclear business value",
            cost_basis="agent loop + API calls",
        ),
        ROIEstimate(
            action_id="full-customer-export-analysis",
            expected_value_usd=500.00,
            estimated_cost_usd=40.00,
            review_cost_usd=20.00,
            confidence=0.90,
            reversible=False,
            value_basis="compliance review avoided",
            cost_basis="model, retrieval, reviewer time",
        ),
    ]

    for estimate in examples:
        result = gate.evaluate(estimate, policy)
        receipt = gate.receipt(result)
        print(f"{estimate.action_id}: {result.decision.value} - {result.reason}")
        print(f"  net=${estimate.net_expected_value_usd:.2f}, cost=${estimate.total_expected_cost_usd:.2f}, receipt={receipt['receipt_id']}")


if __name__ == "__main__":
    main()
