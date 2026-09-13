import unittest

from lib.customer_modules import (
    CustomerModuleOrder,
    CustomModuleRequirement,
    ModuleOrderMode,
    ModuleSelection,
    default_customer_module_catalog,
)


class CustomerModuleCatalogTests(unittest.TestCase):
    def test_starter_catalog_contains_horizontal_business_modules(self):
        catalog = default_customer_module_catalog()
        ids = {recipe.module_id for recipe in catalog.recipes}
        self.assertTrue(
            {
                "software",
                "shadow-discovery",
                "innovation",
                "research",
                "compliance",
                "hiring",
                "contracting",
            }.issubset(ids)
        )
        self.assertTrue(all(recipe.grants_authority is False for recipe in catalog.recipes))

    def test_ready_module_order_resolves_like_a_menu_item(self):
        catalog = default_customer_module_catalog()
        order = CustomerModuleOrder(
            order_ref="order:research:1",
            customer_ref="customer:acme",
            desired_outcome="Understand regulatory exposure before launch",
            selections=(
                ModuleSelection(
                    module_id="research",
                    options={"depth": "deep", "jurisdictions": ["EU", "US"]},
                ),
            ),
        )
        resolved = catalog.resolve(order)
        self.assertIs(resolved.mode, ModuleOrderMode.READY)
        self.assertEqual(resolved.module_ids, ("research",))
        self.assertIn("research-report", resolved.output_types)
        self.assertFalse(resolved.grants_authority)

    def test_hybrid_order_combines_modules_and_custom_requirements(self):
        catalog = default_customer_module_catalog()
        order = CustomerModuleOrder(
            order_ref="order:hybrid:1",
            customer_ref="customer:acme",
            desired_outcome="Find and contract a specialist for an AI compliance project",
            selections=(
                ModuleSelection(module_id="hiring", options={"seniority": "principal"}),
                ModuleSelection(module_id="contracting", options={"contract_type": "consulting"}),
            ),
            custom_requirements=(
                CustomModuleRequirement(
                    requirement_ref="req:1",
                    description="Candidate must have production AI governance experience",
                    acceptance_criterion="shortlist includes evidence for production AI governance experience",
                ),
            ),
        )
        resolved = catalog.resolve(order)
        self.assertIs(resolved.mode, ModuleOrderMode.HYBRID)
        self.assertEqual(resolved.module_ids, ("hiring", "contracting"))
        self.assertIn("shortlist", resolved.output_types)
        self.assertIn("contract-draft", resolved.output_types)

    def test_custom_module_order_does_not_require_a_predefined_vertical(self):
        catalog = default_customer_module_catalog()
        order = CustomerModuleOrder(
            order_ref="order:custom:1",
            customer_ref="customer:acme",
            desired_outcome="Create a completely new business capability",
            custom_requirements=(
                CustomModuleRequirement(
                    requirement_ref="req:new",
                    description="Design and validate the capability from scratch",
                    acceptance_criterion="customer approves evidence-backed operating design",
                ),
            ),
        )
        resolved = catalog.resolve(order)
        self.assertIs(resolved.mode, ModuleOrderMode.CUSTOM)
        self.assertEqual(resolved.module_ids, ())
        self.assertFalse(order.grants_authority)

    def test_unknown_menu_option_fails_closed(self):
        catalog = default_customer_module_catalog()
        order = CustomerModuleOrder(
            order_ref="order:bad",
            customer_ref="customer:acme",
            desired_outcome="Research something",
            selections=(ModuleSelection(module_id="research", options={"magic": True}),),
        )
        with self.assertRaisesRegex(ValueError, "unsupported options"):
            catalog.resolve(order)


if __name__ == "__main__":
    unittest.main()
