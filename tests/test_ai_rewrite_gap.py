"""Description rewrites report their held-out gap and selection optimism."""
import unittest

from skillsmgr import ai_skills


def _summary(train_hits: int, hold_hits: int, total: int = 4) -> dict:
    rows = []
    for split, hits in (("train", train_hits), ("holdout", hold_hits)):
        for n in range(total):
            rows.append({"split": split, "expected": "x", "_positive": True, "_focus": "x", "answered": 1,
                         "choices": {"x": 1} if n < hits else {"(none)": 1}})
    return {"prompts": rows}


class GapTests(unittest.TestCase):
    def test_tiny_splits_give_no_gap(self):
        self.assertIsNone(ai_skills._gap(_summary(3, 0, total=3)))  # 3 answers per split

    def test_gap_is_train_minus_held_out(self):
        self.assertEqual(ai_skills._gap(_summary(4, 2)), 0.5)
        self.assertEqual(ai_skills._gap(_summary(2, 2)), 0.0)
        self.assertIsNone(ai_skills._gap({"prompts": []}))

    def test_repeats_do_not_count_as_additional_prompts_for_the_gap(self):
        summary = _summary(1, 0, total=1)
        for row in summary["prompts"]:
            row["answered"] = 5
            row["choices"] = {next(iter(row["choices"])): 5}
        self.assertIsNone(ai_skills._gap(summary))

    def test_missing_holdout_scores_cannot_support_a_recommendation(self):
        baseline = _summary(2, 0)
        candidate = _summary(4, 0)
        baseline["prompts"] = [row for row in baseline["prompts"] if row["split"] == "train"]
        candidate["prompts"] = [row for row in candidate["prompts"] if row["split"] == "train"]
        result = ai_skills._ranked(baseline, [({"description": "candidate"}, candidate)])
        self.assertFalse(result["candidates"][0]["recommended"])

    def test_overfit_flag_and_selection_note(self):
        baseline = _summary(2, 2)
        ranked = ai_skills._ranked(baseline, [({"description": "fits examples"}, _summary(4, 1)),
                                              ({"description": "general"}, _summary(3, 3))])
        by_text = {c["description"]: c for c in ranked["candidates"]}
        self.assertTrue(by_text["fits examples"]["overfit"])
        self.assertFalse(by_text["general"]["overfit"])
        self.assertIn("best of 2", ranked["selection_note"])
        single = ai_skills._ranked(_summary(2, 2), [({"description": "only"}, _summary(3, 3))])
        self.assertEqual(single["selection_note"], "")

    def test_malformed_routing_answers_are_ignored_or_counted_as_invalid(self):
        answers = {}
        batch = [{"id": "p1"}, {"id": "p2"}]
        names = {"x"}
        ai_skills._record_answers({"answers": 1}, batch, names, answers)
        self.assertEqual(answers, {})
        ai_skills._record_answers({"answers": [
            {"id": ["p1"], "skill": "x"},
            {"id": "p1", "skill": "x", "runner_up": {"name": "x"}},
            {"id": "p2", "skill": ["x"]},
        ]}, batch, names, answers)
        self.assertEqual(answers, {"p1": ("x", None), "p2": ("?invalid", None)})


if __name__ == "__main__":
    unittest.main()
