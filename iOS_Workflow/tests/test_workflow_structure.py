import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkflowStructureTests(unittest.TestCase):
    def test_testing_route_references_existing_files(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        gate = (ROOT / "checklists/pre-commit-review.md").read_text(encoding="utf-8")
        self.assertIn("standards/testing.md", agents)
        self.assertIn("checklists/testing.md", gate)
        self.assertTrue((ROOT / "standards/testing.md").is_file())
        self.assertTrue((ROOT / "checklists/testing.md").is_file())

    def test_testing_templates_contain_evidence_fields(self):
        plan = (ROOT / "templates/testing/test-plan.md").read_text(encoding="utf-8")
        report = (ROOT / "templates/testing/test-report.md").read_text(encoding="utf-8")
        self.assertIn("验收与测试映射", plan)
        self.assertIn("destination", plan)
        self.assertIn("证据键", report)
        self.assertIn("flaky", report)

    def test_testing_standard_limits_flaky_reruns(self):
        standard = (ROOT / "standards/testing.md").read_text(encoding="utf-8")
        self.assertIn("最多额外复跑一次", standard)
        self.assertIn("禁止无上限重试", standard)
        self.assertIn("证据键", standard)


if __name__ == "__main__":
    unittest.main()
