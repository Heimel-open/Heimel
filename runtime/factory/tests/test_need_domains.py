import unittest

from lib.need_domains import (
    WELLBEING,
    ConfirmedNeed,
    NeedHypothesis,
    NeedToDoneContract,
    confirm_need,
    get_need_domain,
)


class NeedDomainTests(unittest.TestCase):
    def test_wellbeing_is_broader_than_wellness(self):
        self.assertEqual(WELLBEING.domain_id, "wellbeing")
        self.assertIn("livsendring", WELLBEING.definition)
        self.assertIn("bredere enn wellness", WELLBEING.definition)

    def test_wellbeing_includes_life_outlook_and_opportunity_changes(self):
        examples = " | ".join(WELLBEING.examples)
        for expected in (
            "ferie og reise",
            "dating, partner og relasjoner",
            "utdanning, læring og ferdigheter",
            "bedre jobb, karriere og inntekt",
            "bil, mobilitet og andre ønskede eiendeler",
            "nye muligheter og tilgang til miljøer eller erfaringer",
        ):
            self.assertIn(expected, examples)

    def test_domain_lookup_fails_closed(self):
        self.assertIs(get_need_domain("wellbeing"), WELLBEING)
        with self.assertRaisesRegex(ValueError, "unknown need domain"):
            get_need_domain("unknown")

    def test_need_is_only_a_hypothesis_until_human_confirmation(self):
        hypothesis = NeedHypothesis(
            need_id="need-1",
            domain_id="wellbeing",
            current_state="job no longer fits desired direction",
            proposed_change="explore a materially better-fitting role",
            rationale="persistent mismatch between stated goals and current work",
            evidence_refs=("observation:1",),
        )
        self.assertFalse(hypothesis.direct_effect_path)

        confirmed = confirm_need(
            hypothesis,
            desired_outcome="move into a role with more autonomy and upside",
            confirmation_ref="human-confirmation:1",
            constraints=("no relocation before January",),
        )
        self.assertTrue(confirmed.confirmed_by_human)
        self.assertEqual(confirmed.need_id, hypothesis.need_id)
        self.assertFalse(confirmed.direct_effect_path)

    def test_unconfirmed_need_cannot_become_mandate(self):
        with self.assertRaisesRegex(ValueError, "explicitly confirmed"):
            ConfirmedNeed(
                need_id="need-2",
                domain_id="wellbeing",
                desired_outcome="find a partner",
                confirmed_by_human=False,
                confirmation_ref="",
            )

    def test_confirmed_need_can_define_done_but_not_bypass_governed_execution(self):
        confirmed = ConfirmedNeed(
            need_id="need-3",
            domain_id="wellbeing",
            desired_outcome="take a restorative two-week holiday",
            confirmed_by_human=True,
            confirmation_ref="human-confirmation:3",
            constraints=("budget <= 4000 EUR",),
        )
        contract = NeedToDoneContract(
            need=confirmed,
            done_definition="trip selected, booked within mandate, completed, and outcome evidence collected",
        )
        self.assertTrue(contract.outcome_evidence_required)
        self.assertFalse(contract.direct_effect_path)


if __name__ == "__main__":
    unittest.main()
