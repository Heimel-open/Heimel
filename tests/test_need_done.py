import unittest

from lib.need_done import DoneTrack, NeedDoneContract, LANE_TRACK, track_for_lane
from lib.opportunity_factory import RevenueLane


class NeedDoneTests(unittest.TestCase):
    def test_every_observed_lane_maps_to_a_done_track(self):
        self.assertEqual(set(LANE_TRACK), set(RevenueLane))

    def test_service_professions_collapse_into_outcomes(self):
        self.assertIs(track_for_lane(RevenueLane.MARKET_INTELLIGENCE), DoneTrack.KNOW)
        self.assertIs(track_for_lane(RevenueLane.DUE_DILIGENCE), DoneTrack.DECIDE)
        self.assertIs(track_for_lane(RevenueLane.ARTICLE_WRITING), DoneTrack.CREATE)
        self.assertIs(track_for_lane(RevenueLane.PR_COMMS), DoneTrack.CONVINCE)
        self.assertIs(track_for_lane(RevenueLane.RECRUITING_SOURCING), DoneTrack.OBTAIN)
        self.assertIs(track_for_lane(RevenueLane.BOOKKEEPING), DoneTrack.OPERATE)
        self.assertIs(track_for_lane(RevenueLane.COMPLIANCE_GRC), DoneTrack.ASSURE)

    def test_new_unseen_service_does_not_require_new_lane(self):
        contract = NeedDoneContract(
            need="Board needs a defensible acquisition recommendation",
            done="Decision memo with evidence, scenarios and recommendation accepted",
            track=DoneTrack.DECIDE,
            deliverables=("decision memo", "evidence pack"),
            required_capabilities=("research", "analysis", "synthesis"),
            automatable_fraction=0.9,
            human_remainder=("board judgement",),
        )
        self.assertEqual(contract.track, DoneTrack.DECIDE)
        self.assertEqual(contract.automatable_fraction, 0.9)

    def test_regulated_work_requires_explicit_human_remainder(self):
        with self.assertRaisesRegex(ValueError, "human remainder"):
            NeedDoneContract(
                need="Need legal opinion",
                done="Signed legal opinion",
                track=DoneTrack.ASSURE,
                automatable_fraction=0.8,
                licensed_role_required=True,
            )

    def test_automation_fraction_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "automatable_fraction"):
            NeedDoneContract("need", "done", DoneTrack.CREATE, automatable_fraction=1.1)


if __name__ == "__main__":
    unittest.main()
