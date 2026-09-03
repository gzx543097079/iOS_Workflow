import json
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

    def test_low_risk_execution_does_not_require_persistence(self):
        requirements = (ROOT / "standards/requirements.md").read_text(encoding="utf-8")
        lifecycle = (ROOT / "standards/requirement-lifecycle.md").read_text(encoding="utf-8")
        self.assertIn("执行本身不是建档条件", requirements)
        self.assertIn("执行本身不是建档条件", lifecycle)

    def test_compact_index_template_only_tracks_active_requirement(self):
        index = json.loads((ROOT / "templates/tracking/index.jsonc").read_text(encoding="utf-8"))
        self.assertEqual(2, index["version"])
        self.assertIn("last_requirement_id", index)
        self.assertIn("active_requirement", index)
        self.assertNotIn("requirements", index)

    def test_resume_prefers_compact_summary(self):
        lifecycle = (ROOT / "standards/requirement-lifecycle.md").read_text(encoding="utf-8")
        template = (ROOT / "templates/tracking/requirement.md").read_text(encoding="utf-8")
        self.assertIn("不默认读取完整档案", lifecycle)
        self.assertIn("## 恢复摘要", template)
        self.assertIn("证据键", template)

    def test_done_is_independent_from_git_delivery(self):
        lifecycle = (ROOT / "standards/requirement-lifecycle.md").read_text(encoding="utf-8")
        checklist = (ROOT / "checklists/requirement-traceability.md").read_text(encoding="utf-8")
        self.assertIn("`done` 与 Git 提交、推送解耦", lifecycle)
        self.assertIn("`done` 不依赖是否已提交或推送", checklist)

    def test_simple_new_module_can_use_brief_design(self):
        standard = (ROOT / "standards/technical-design.md").read_text(encoding="utf-8")
        self.assertIn("简单新增页面或内部模块也可使用 `brief`", standard)
        self.assertIn("“新增模块”本身不自动触发完整设计", standard)


if __name__ == "__main__":
    unittest.main()
