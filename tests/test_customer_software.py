import unittest

from lib.commercial_loop import CustomerAcceptanceRef
from lib.customer_software import (
    CustomerSoftwareOrder,
    CustomRequirement,
    MenuSelection,
    OrderMode,
    default_software_menu,
    to_poc_mission_spec,
)


class CustomerSoftwareTests(unittest.TestCase):
    def test_ready_menu_order_is_horizontal_and_configurable(self):
        order = CustomerSoftwareOrder(
            order_id="order-1",
            customer_ref="customer:acme",
            desired_outcome="Automate lead intake and qualification",
            menu_selections=(
                MenuSelection(
                    item_id="workflow-automation",
                    options={
                        "trigger": "web-form",
                        "systems": ("crm", "email"),
                    },
                ),
            ),
        )

        resolved = default_software_menu().resolve(order)

        self.assertIs(resolved.mode, OrderMode.READY_MENU)
        self.assertEqual(resolved.recipe_refs, ("recipe:workflow-automation:v1",))
        self.assertFalse(order.grants_authority)
        self.assertFalse(resolved.grants_authority)

    def test_fully_custom_order_requires_no_vertical_or_menu_item(self):
        order = CustomerSoftwareOrder(
            order_id="order-2",
            customer_ref="customer:tiny-or-global",
            desired_outcome="Build exactly the software described by the customer",
            custom_requirements=(
                CustomRequirement(
                    requirement_id="req-1",
                    description="Operator uploads a file and receives a validated result",
                    acceptance_criterion="valid fixture returns the agreed result",
                ),
            ),
            integrations=("customer-api",),
            constraints=("EU data residency",),
        )

        resolved = default_software_menu().resolve(order)

        self.assertIs(resolved.mode, OrderMode.CUSTOM_MENU)
        self.assertEqual(resolved.recipe_refs, ())
        self.assertIn("valid fixture returns the agreed result", resolved.acceptance_criteria)

    def test_hybrid_order_combines_ready_recipe_with_custom_requirements(self):
        order = CustomerSoftwareOrder(
            order_id="order-3",
            customer_ref="customer:acme",
            desired_outcome="Agent that updates two existing systems and uses our approval rule",
            menu_selections=(
                MenuSelection(
                    item_id="ai-agent",
                    options={"tools": ("crm", "erp"), "channels": ("web",)},
                ),
                MenuSelection(
                    item_id="system-integration",
                    options={"source": "crm", "destination": "erp"},
                ),
            ),
            custom_requirements=(
                CustomRequirement(
                    requirement_id="req-approval",
                    description="Use customer's bespoke approval rule before update",
                    acceptance_criterion="updates never occur without the agreed approval condition",
                ),
            ),
        )

        resolved = default_software_menu().resolve(order)

        self.assertIs(resolved.mode, OrderMode.HYBRID)
        self.assertEqual(len(resolved.recipe_refs), 2)
        self.assertIn(
            "updates never occur without the agreed approval condition",
            resolved.acceptance_criteria,
        )

    def test_unknown_menu_option_fails_closed(self):
        order = CustomerSoftwareOrder(
            order_id="order-4",
            customer_ref="customer:acme",
            desired_outcome="Automate a workflow",
            menu_selections=(
                MenuSelection(
                    item_id="workflow-automation",
                    options={"invent_new_architecture": True},
                ),
            ),
        )

        with self.assertRaisesRegex(ValueError, "unsupported options"):
            default_software_menu().resolve(order)

    def test_order_requires_menu_or_custom_requirement(self):
        with self.assertRaisesRegex(ValueError, "menu selection or custom requirement"):
            CustomerSoftwareOrder(
                order_id="order-5",
                customer_ref="customer:acme",
                desired_outcome="Something",
            )

    def test_accepted_customer_order_materializes_to_normal_poc_spec(self):
        order = CustomerSoftwareOrder(
            order_id="order-6",
            customer_ref="customer:acme",
            desired_outcome="Build customer portal connected to billing",
            menu_selections=(
                MenuSelection(
                    item_id="customer-app",
                    options={"surface": "web", "payments": "customer-provider"},
                ),
            ),
            additional_acceptance_criteria=("customer can complete the target purchase",),
        )
        resolved = default_software_menu().resolve(order)
        acceptance = CustomerAcceptanceRef(
            subject=resolved.order_id,
            acceptance_ref="acceptance:order-6:v1",
            accepted_by="customer-authorized-representative",
        )

        spec = to_poc_mission_spec(
            resolved,
            acceptance,
            target_repo="nsolland/customer-acme",
            owned_files=("src/**", "tests/**"),
            canonical_base_sha="a" * 40,
        )

        self.assertEqual(spec.customer_ref, "customer:acme")
        self.assertEqual(spec.spec_ref, "customer-order:order-6")
        self.assertIn("recipe:customer-app:v1", spec.dependencies)
        self.assertTrue(spec.acceptance_criteria)

    def test_acceptance_for_another_order_cannot_start_build(self):
        order = CustomerSoftwareOrder(
            order_id="order-7",
            customer_ref="customer:acme",
            desired_outcome="Build internal tool",
            menu_selections=(MenuSelection(item_id="internal-app"),),
        )
        resolved = default_software_menu().resolve(order)
        acceptance = CustomerAcceptanceRef(
            subject="order-other",
            acceptance_ref="acceptance:other",
            accepted_by="customer-authorized-representative",
        )

        with self.assertRaisesRegex(ValueError, "not bound"):
            to_poc_mission_spec(
                resolved,
                acceptance,
                target_repo="nsolland/customer-acme",
                owned_files=("src/**", "tests/**"),
            )


if __name__ == "__main__":
    unittest.main()
