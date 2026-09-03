import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_FILE = ROOT / ".agents/skills/ios-workflow/SKILL.md"
CASES_FILE = ROOT / "tests/fixtures/skill-trigger-cases.json"


def _frontmatter_description() -> str:
    lines = SKILL_FILE.read_text(encoding="utf-8").splitlines()
    for line in lines[1:]:
        if line.startswith("description:"):
            return line.removeprefix("description:").strip().strip('"')
        if line == "---":
            break
    return ""


class SkillTriggerEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(CASES_FILE.read_text(encoding="utf-8"))
        cls.cases = cls.corpus["cases"]

    def test_corpus_targets_ios_workflow(self):
        self.assertEqual("ios-workflow", self.corpus["skill"])
        self.assertTrue(self.corpus["purpose"])
        self.assertGreaterEqual(len(self.cases), 12)

    def test_cases_have_complete_unique_contracts(self):
        required = {"id", "language", "category", "prompt", "expected_activation", "reason"}
        identifiers = [case["id"] for case in self.cases]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for case in self.cases:
            self.assertEqual(required, set(case))
            self.assertIn(case["language"], {"zh", "en", "mixed"})
            self.assertIsInstance(case["expected_activation"], bool)
            self.assertTrue(case["prompt"].strip())
            self.assertTrue(case["reason"].strip())

    def test_corpus_balances_activation_and_rejection(self):
        outcomes = [case["expected_activation"] for case in self.cases]
        self.assertEqual(outcomes.count(True), outcomes.count(False))
        self.assertGreaterEqual(outcomes.count(True), 6)

    def test_corpus_covers_languages_and_boundaries(self):
        languages = {case["language"] for case in self.cases}
        categories = {case["category"] for case in self.cases}
        self.assertEqual({"zh", "en", "mixed"}, languages)
        self.assertTrue(
            {"ios_feature", "ios_debugging", "ios_delivery", "explicit_invocation",
             "unrelated_platform", "ambiguous_technology", "ios_boundary"}.issubset(categories)
        )
        boundary_outcomes = {
            case["expected_activation"]
            for case in self.cases
            if case["category"] == "ios_boundary"
        }
        self.assertEqual({True, False}, boundary_outcomes)

    def test_explicit_invocation_case_is_present(self):
        explicit_cases = [case for case in self.cases if "$ios-workflow" in case["prompt"]]
        self.assertEqual(1, len(explicit_cases))
        self.assertTrue(explicit_cases[0]["expected_activation"])

    def test_description_declares_domain_and_exclusion_boundary(self):
        description = _frontmatter_description()
        self.assertIn("iOS", description)
        self.assertTrue(any(term in description for term in ("Swift", "UIKit", "SwiftUI", "Xcode")))
        self.assertTrue(any(term in description for term in ("不要用于", "不适用", "无关")))


if __name__ == "__main__":
    unittest.main()
