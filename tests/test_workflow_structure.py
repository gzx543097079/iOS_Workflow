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

    def test_runtime_records_use_hidden_workflow_directory(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        lifecycle = (SKILL_ROOT / "references/standards/requirement-lifecycle.md").read_text(encoding="utf-8")
        self.assertFalse((ROOT / "iOSFlowRecords").exists())
        self.assertFalse((ROOT / ".iOSFlowRecords").exists())
        self.assertIn("<项目根目录>/.ios-workflow/index.jsonc", skill)
        self.assertIn("本工作流约定，不属于 Codex 官方 Skill 结构", lifecycle)

    def test_document_intake_and_project_local_handoff_are_routed(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        intake = (SKILL_ROOT / "references/standards/requirement-intake.md").read_text(encoding="utf-8")
        lifecycle = (SKILL_ROOT / "references/standards/requirement-lifecycle.md").read_text(encoding="utf-8")
        evidence = (SKILL_ROOT / "references/standards/tracking-evidence.md").read_text(encoding="utf-8")
        sync = (SKILL_ROOT / "references/standards/tracking-sync.md").read_text(encoding="utf-8")
        self.assertIn("references/standards/requirement-intake.md", skill)
        self.assertIn("生成器不解析自然语言", intake)
        self.assertIn("示例是结构参考，不是默认值", intake)
        self.assertIn("不写入 Skill", lifecycle)
        self.assertIn("progress_validation.py", evidence)
        self.assertIn("仅在当前设备保存文件无法保证跨设备不丢进度", sync)
        self.assertIn("不读取、不核对初始生成配置", lifecycle)

    def test_portable_tracking_templates_do_not_point_to_shared_project_groups(self):
        index = json.loads((SKILL_ROOT / "assets/templates/tracking/index.jsonc").read_text())
        progress = json.loads((SKILL_ROOT / "assets/templates/tracking/progress.json").read_text())
        handoff = (SKILL_ROOT / "assets/templates/tracking/handoff.md").read_text()
        self.assertEqual(index["active_requirement"]["project"], ".")
        self.assertTrue(index["active_requirement"]["file"].startswith(".ios-workflow/requirements/"))
        self.assertEqual(progress, {"schema_version": 1, "items": []})
        self.assertIn("未核实", handoff)
        self.assertIn("未提交或未推送", handoff)

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

    def test_release_route_and_gate_reference_existing_files(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        gate = (SKILL_ROOT / "references/checklists/pre-commit-review.md").read_text(encoding="utf-8")
        self.assertIn("references/standards/release-distribution.md", skill)
        self.assertIn("references/checklists/release-distribution.md", gate)
        self.assertTrue((SKILL_ROOT / "references/standards/release-distribution.md").is_file())
        self.assertTrue((SKILL_ROOT / "references/checklists/release-distribution.md").is_file())

    def test_release_standard_separates_external_actions_and_states(self):
        standard = (SKILL_ROOT / "references/standards/release-distribution.md").read_text(encoding="utf-8")
        self.assertIn("只有用户当前要求已经明确包含对应动作时才执行", standard)
        self.assertIn("上传命令成功不等于构建已可测试、可送审或已发布", standard)
        self.assertIn("更高 Build", standard)
        self.assertIn("已安装的 App Store 二进制不能直接降级", standard)

    def test_release_templates_contain_traceability_and_recovery_fields(self):
        plan = (SKILL_ROOT / "assets/templates/release/release-plan.md").read_text(encoding="utf-8")
        report = (SKILL_ROOT / "assets/templates/release/release-report.md").read_text(encoding="utf-8")
        self.assertIn("源提交或 Tag", plan)
        self.assertIn("目标渠道", plan)
        self.assertIn("Archive", plan)
        self.assertIn("监控与回退", plan)
        self.assertIn("处理状态", report)
        self.assertIn("下一状态与负责人", report)
        self.assertIn("不记录证书私钥", report)

    def test_low_risk_execution_does_not_require_persistence(self):
        requirements = (SKILL_ROOT / "references/standards/requirements.md").read_text(encoding="utf-8")
        start = (SKILL_ROOT / "references/standards/tracking-start.md").read_text(encoding="utf-8")
        self.assertIn("执行本身不是建档条件", requirements)
        self.assertIn("执行本身不是建档条件", start)

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
        resume = (SKILL_ROOT / "references/standards/tracking-resume.md").read_text(encoding="utf-8")
        template = (SKILL_ROOT / "assets/templates/tracking/requirement.md").read_text(encoding="utf-8")
        self.assertIn("不默认读取完整档案", resume)
        self.assertIn("load_resume_context", resume)
        self.assertIn("truncated_fields", resume)
        self.assertIn("## 恢复摘要", template)
        self.assertIn("证据键", template)

    def test_done_is_independent_from_git_delivery(self):
        evidence = (SKILL_ROOT / "references/standards/tracking-evidence.md").read_text(encoding="utf-8")
        checklist = (SKILL_ROOT / "references/checklists/requirement-traceability.md").read_text(encoding="utf-8")
        self.assertIn("`done` 与 Git 提交、推送解耦", evidence)
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
        self.assertIn("生成器读取已保存实例并校验", skill)
        self.assertIn("references/standards/project-configuration.md", skill)
        self.assertIn("load_project_instance", generation)
        self.assertIn("不把完整配置输出到模型上下文", generation)

    def test_existing_projects_do_not_check_generation_configuration(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        gate = (SKILL_ROOT / "references/checklists/pre-commit-review.md").read_text(encoding="utf-8")
        self.assertIn("不读取、不核对初始生成配置", skill)
        self.assertIn("历史生成配置不构成提交或推送门禁", gate)
        self.assertFalse((SKILL_ROOT / "assets/config/project.example.jsonc").exists())

    def test_documentation_changes_do_not_invalidate_test_evidence(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        testing = (SKILL_ROOT / "references/standards/testing.md").read_text(encoding="utf-8")
        self.assertIn("纯文档、运行记录或版本号", skill)
        self.assertIn("纯文档、运行记录、版本号", testing)

    def test_git_delivery_does_not_create_writeback_commits(self):
        sync = (SKILL_ROOT / "references/standards/tracking-sync.md").read_text(encoding="utf-8")
        gate = (SKILL_ROOT / "references/checklists/pre-commit-review.md").read_text(encoding="utf-8")
        template = (SKILL_ROOT / "assets/templates/tracking/requirement.md").read_text(encoding="utf-8")
        self.assertIn("不得仅为写回当前提交 hash", sync)
        self.assertIn("不得为了回写本次提交 hash", gate)
        self.assertNotIn("delivery_status:", template)

    def test_tracking_entry_links_directly_to_task_specific_references(self):
        standards = SKILL_ROOT / "references/standards"
        entry = (standards / "requirement-lifecycle.md").read_text(encoding="utf-8")
        for name in ("tracking-start.md", "tracking-evidence.md", "tracking-resume.md", "tracking-sync.md"):
            with self.subTest(name=name):
                self.assertIn(f"]({name})", entry)
                self.assertTrue((standards / name).is_file())
        self.assertIn("不依次加载全部生命周期规则", entry)
        self.assertNotIn("validate_progress_scope", entry)
        self.assertNotIn("load_resume_context", entry)


if __name__ == "__main__":
    unittest.main()
