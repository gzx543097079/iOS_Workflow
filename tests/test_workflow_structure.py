import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / ".agents/skills/ios-workflow"


class WorkflowStructureTests(unittest.TestCase):
    def test_repository_uses_official_skill_entrypoint(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("$ios-workflow", agents)
        self.assertIn("name: ios-workflow", skill)
        self.assertIn("description:", skill)
        self.assertNotIn("[TODO", skill)

    def test_testing_route_references_existing_files(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        gate = (SKILL_ROOT / "references/checklists/pre-commit-review.md").read_text(encoding="utf-8")
        self.assertIn("references/standards/testing.md", skill)
        self.assertIn("references/checklists/testing.md", gate)
        self.assertTrue((SKILL_ROOT / "references/standards/testing.md").is_file())
        self.assertTrue((SKILL_ROOT / "references/checklists/testing.md").is_file())

    def test_testing_templates_contain_evidence_fields(self):
        plan = (SKILL_ROOT / "assets/templates/testing/test-plan.md").read_text(encoding="utf-8")
        report = (SKILL_ROOT / "assets/templates/testing/test-report.md").read_text(encoding="utf-8")
        self.assertIn("验收与测试映射", plan)
        self.assertIn("destination", plan)
        self.assertIn("证据键", report)
        self.assertIn("flaky", report)

    def test_testing_standard_limits_flaky_reruns(self):
        standard = (SKILL_ROOT / "references/standards/testing.md").read_text(encoding="utf-8")
        self.assertIn("最多额外复跑一次", standard)
        self.assertIn("禁止无上限重试", standard)
        self.assertIn("证据键", standard)

    def test_low_risk_execution_does_not_require_persistence(self):
        requirements = (SKILL_ROOT / "references/standards/requirements.md").read_text(encoding="utf-8")
        lifecycle = (SKILL_ROOT / "references/standards/requirement-lifecycle.md").read_text(encoding="utf-8")
        self.assertIn("执行本身不是建档条件", requirements)
        self.assertIn("执行本身不是建档条件", lifecycle)

    def test_compact_index_template_only_tracks_active_requirement(self):
        index = json.loads((SKILL_ROOT / "assets/templates/tracking/index.jsonc").read_text(encoding="utf-8"))
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
        lifecycle = (SKILL_ROOT / "references/standards/requirement-lifecycle.md").read_text(encoding="utf-8")
        template = (SKILL_ROOT / "assets/templates/tracking/requirement.md").read_text(encoding="utf-8")
        self.assertIn("不默认读取完整档案", lifecycle)
        self.assertIn("## 恢复摘要", template)
        self.assertIn("证据键", template)

    def test_done_is_independent_from_git_delivery(self):
        lifecycle = (SKILL_ROOT / "references/standards/requirement-lifecycle.md").read_text(encoding="utf-8")
        checklist = (SKILL_ROOT / "references/checklists/requirement-traceability.md").read_text(encoding="utf-8")
        self.assertIn("`done` 与 Git 提交、推送解耦", lifecycle)
        self.assertIn("`done` 不依赖是否已提交或推送", checklist)

    def test_simple_new_module_can_use_brief_design(self):
        standard = (SKILL_ROOT / "references/standards/technical-design.md").read_text(encoding="utf-8")
        self.assertIn("简单新增页面或内部模块也可使用 `brief`", standard)
        self.assertIn("“新增模块”本身不自动触发完整设计", standard)

    def test_low_risk_routes_avoid_full_requirement_and_design_loading(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("低风险单轮任务直接在上下文形成精简需求卡", skill)
        self.assertIn("可在上下文形成 inline brief", skill)
        self.assertIn("设计边界不明确或触发完整设计时", skill)

    def test_generator_consumes_configuration_without_model_context(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        generation = (SKILL_ROOT / "references/standards/project-generation.md").read_text(encoding="utf-8")
        self.assertIn("配置和 DesignTokens 由生成器直接读取", skill)
        self.assertIn("不把完整配置输出到模型上下文", generation)

    def test_documentation_changes_do_not_invalidate_test_evidence(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        testing = (SKILL_ROOT / "references/standards/testing.md").read_text(encoding="utf-8")
        self.assertIn("纯文档、运行记录或版本号", skill)
        self.assertIn("纯文档、运行记录、版本号", testing)

    def test_git_delivery_does_not_create_writeback_commits(self):
        lifecycle = (SKILL_ROOT / "references/standards/requirement-lifecycle.md").read_text(encoding="utf-8")
        gate = (SKILL_ROOT / "references/checklists/pre-commit-review.md").read_text(encoding="utf-8")
        template = (SKILL_ROOT / "assets/templates/tracking/requirement.md").read_text(encoding="utf-8")
        self.assertIn("不得仅为写回当前提交 hash", lifecycle)
        self.assertIn("不得为了回写本次提交 hash", gate)
        self.assertNotIn("delivery_status:", template)


if __name__ == "__main__":
    unittest.main()
