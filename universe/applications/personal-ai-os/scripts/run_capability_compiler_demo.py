#!/usr/bin/env python3
from paios.capability_compiler import run_invoice_demo


def main() -> None:
    certificate = run_invoice_demo()
    print(f"outcome={certificate.outcome_id}")
    print(f"realized={certificate.realized}")
    print(f"minimal={certificate.minimal}")
    print(f"resources={','.join(certificate.resource_ids)}")
    print(f"total_cost={certificate.total_cost:.2f}")
    for item in certificate.ablations:
        print(
            f"ablate={item.removed_resource_id} "
            f"still_realized={item.still_realized}"
        )


if __name__ == "__main__":
    main()
