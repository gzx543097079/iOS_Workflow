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
        self.assertEqual(3, index["version"])
        self.assertIn("last_requirement_id", index)
        self.assertIn("active_requirement", index)
        self.assertNotIn("requirements", index)
        self.assertEqual(
            {"current_step", "next_action", "blockers", "evidence_key", "scope_version"},
            {key for key in index["active_requirement"] if key in {
                "current_step", "next_action", "blockers", "evidence_key", "scope_version"
            }},
        )

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

    def test_low_risk_routes_avoid_full_requirement_and_design_loading(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("低风险单轮任务直接在上下文形成精简需求卡", agents)
        self.assertIn("可在上下文形成 inline brief", agents)
        self.assertIn("设计边界不明确或触发完整设计时才读取", agents)

    def test_generator_consumes_configuration_without_model_context(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        generation = (ROOT / "standards/project-generation.md").read_text(encoding="utf-8")
        self.assertIn("配置和 DesignTokens 由生成器直接读取校验", agents)
        self.assertIn("不把完整配置输出到模型上下文", generation)

    def test_documentation_changes_do_not_invalidate_test_evidence(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        testing = (ROOT / "standards/testing.md").read_text(encoding="utf-8")
        self.assertIn("纯文档、运行记录、版本号", agents)
        self.assertIn("纯文档、运行记录、版本号", testing)

    def test_git_delivery_does_not_create_writeback_commits(self):
        lifecycle = (ROOT / "standards/requirement-lifecycle.md").read_text(encoding="utf-8")
        gate = (ROOT / "checklists/pre-commit-review.md").read_text(encoding="utf-8")
        template = (ROOT / "templates/tracking/requirement.md").read_text(encoding="utf-8")
        self.assertIn("不得仅为写回当前提交 hash", lifecycle)
        self.assertIn("不得为了回写本次提交 hash", gate)
        self.assertNotIn("delivery_status:", template)


if __name__ == "__main__":
    unittest.main()
