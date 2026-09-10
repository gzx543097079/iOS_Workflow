"""Synthetic event fixtures test the evaluator, not actual model behavior."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_module_loading import command_reads, evaluate, load_case, parse_trace, run_case
sys.path.insert(0, str(ROOT / ".agents/skills/ios-workflow/scripts"))
from resume_context import load_resume_context


def command_event(identifier, command, exit_code=0):
    return {"type": "item.completed", "item": {"type": "command_execution", "id": identifier,
            "command": command, "exit_code": exit_code, "status": "completed", "aggregated_output": "synthetic test output"}}


def completed(usage=None):
    result = {"type": "turn.completed"}
    if usage is not None:
        result["usage"] = usage
    return result


class ModuleLoadingEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.skill = self.project / ".agents/skills/ios-workflow"
        self.case = load_case("resume-only")

    def parse(self, events):
        path = self.root / "events.jsonl"
        path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
        return parse_trace(path, self.project)

    def test_expected_cases_cover_nine_representative_contexts(self):
        corpus = json.loads((ROOT / "tests/fixtures/module-loading-cases.json").read_text())
        identifiers = [case["id"] for case in corpus["cases"]]
        self.assertEqual({"existing-app-iteration", "low-risk-code-change", "first-generation", "resume-only", "cross-device-resume", "save-stage-with-failure",
                          "push-only", "workflow-release", "non-ios-docs"}, set(identifiers))
        self.assertEqual(9, len(identifiers))
        for case in corpus["cases"]:
            self.assertTrue(case["prompt"])
            self.assertEqual(1, case["max_reads_per_module"])
            self.assertNotIn("actual", case)
            self.assertNotIn("usage", case)

    def test_resume_fixtures_match_current_tracking_contract_and_distinguish_device_switch(self):
        for identifier in ("resume-only", "cross-device-resume"):
            case = load_case(identifier)
            project = self.root / identifier
            for relative, content in case["files"].items():
                target = project / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            result = load_resume_context(project)
            self.assertEqual([], result["errors"], identifier)
            self.assertTrue(result["tracking_state_checked"])
        sync = "references/standards/tracking-sync.md"
        self.assertIn(sync, load_case("resume-only")["forbidden_modules"])
        self.assertIn(sync, load_case("cross-device-resume")["expected_modules"])

    def test_existing_app_iteration_has_a_project_and_new_version_requirements(self):
        files = load_case("existing-app-iteration")["files"]
        self.assertIn("ExistingApp.xcodeproj/project.pbxproj", files)
        self.assertIn("PBXProject", files["ExistingApp.xcodeproj/project.pbxproj"])
        self.assertIn("Requirements-v1.1.md", files)
        self.assertIn("App/Counter.swift", files)

    def test_successful_native_reads_are_actual_and_usage_is_reported_separately(self):
        events = [command_event("read", "/bin/zsh -lc 'cat .agents/skills/ios-workflow/SKILL.md .agents/skills/ios-workflow/references/standards/tracking-resume.md'"),
                  completed({"input_tokens": 100, "cached_input_tokens": 60, "output_tokens": 12})]
        actual = self.parse(events)
        result = evaluate(self.case, actual)
        self.assertEqual("pass", result["status"])
        self.assertEqual(self.case["expected_modules"], result["loaded_modules"])
        self.assertEqual({"input_tokens": 100, "cached_input_tokens": 60, "output_tokens": 12}, actual["usage"])
        self.assertEqual("reported", result["token_status"])

    def test_prompt_and_agent_claims_and_filename_listings_are_not_reads(self):
        actual = self.parse([{"type": "item.completed", "item": {"type": "agent_message", "text": "I read SKILL.md and tracking-resume.md"}},
                             command_event("listing", "rg --files .agents/skills/ios-workflow"), completed()])
        result = evaluate(self.case, actual)
        self.assertEqual([], result["loaded_modules"])
        self.assertEqual("fail", result["status"])
        self.assertEqual(self.case["expected_modules"], result["missing_expected"])

    def test_filename_only_and_count_only_searches_do_not_load_module_content(self):
        for command in ("rg -l rule", "rg --files-with-matches rule", "rg -c rule", "rg --count rule",
                        "grep -nl rule", "grep -l rule", "grep --count rule", "grep -c rule"):
            command += " .agents/skills/ios-workflow/SKILL.md"
            result = evaluate(self.case, self.parse([command_event("summary", command), completed()]))
            self.assertEqual([], result["loaded_modules"], command)
            self.assertEqual("inconclusive", result["status"], command)

    def test_forbidden_unexpected_and_repeated_reads_are_reported(self):
        actual = self.parse([command_event("first", "cat .agents/skills/ios-workflow/SKILL.md"),
                             command_event("again", "sed -n '1,80p' .agents/skills/ios-workflow/SKILL.md"),
                             command_event("forbidden", "cat .agents/skills/ios-workflow/references/standards/project-configuration.md"), completed()])
        result = evaluate(self.case, actual)
        self.assertEqual("fail", result["status"])
        self.assertEqual({"SKILL.md": 2}, result["repeated_reads"])
        self.assertIn("references/standards/project-configuration.md", result["forbidden_loaded"])
        self.assertIn("references/standards/project-configuration.md", result["unexpected_loaded"])

    def test_failed_or_opaque_commands_do_not_prove_absence(self):
        for event in (command_event("failed", "cat .agents/skills/ios-workflow/SKILL.md", 1),
                      command_event("python", "python3 -c 'print(open(secret_path).read())'"),
                      command_event("shell", "cat $(find .agents -name SKILL.md)"),
                      command_event("show", "git show HEAD:.agents/skills/ios-workflow/SKILL.md")):
            with self.subTest(event=event):
                result = evaluate(self.case, self.parse([event, completed()]))
                self.assertEqual("inconclusive", result["status"])
                self.assertTrue(result["actual"]["unobserved_actions"])

    def test_unknown_tools_and_partial_traces_are_inconclusive(self):
        for events in ([{"type": "item.completed", "item": {"type": "mcp_tool_call"}}, completed()],
                       [{"type": "future.file_read", "path": "SKILL.md"}, completed()],
                       [{"type": "thread.started"}], [completed(), {"type": "turn.failed"}]):
            with self.subTest(events=events):
                self.assertEqual("inconclusive", evaluate(self.case, self.parse(events))["status"])

    def test_truncated_new_turn_is_not_hidden_by_previous_completion(self):
        events = [completed({"input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 1}), {"type": "turn.started"}]
        result = evaluate(load_case("non-ios-docs"), self.parse(events))
        self.assertEqual("inconclusive", result["status"])
        self.assertFalse(result["actual"]["completed"])
        self.assertEqual("unavailable_or_partial", result["token_status"])

    def test_searching_project_directories_is_not_treated_as_proof_of_no_skill_reads(self):
        for command in ("rg -n rule .", "grep -R rule .", "rg rule ./", "rg rule .agents"):
            result = evaluate(load_case("non-ios-docs"), self.parse([command_event("search", command), completed()]))
            self.assertEqual("inconclusive", result["status"], command)

    def test_zero_output_read_does_not_count_as_loading_module_content(self):
        event = command_event("empty", "head -n 0 .agents/skills/ios-workflow/SKILL.md")
        event["item"]["aggregated_output"] = ""
        result = evaluate(self.case, self.parse([event, completed()]))
        self.assertEqual([], result["loaded_modules"])
        self.assertEqual("inconclusive", result["status"])

    def test_missing_usage_remains_unknown_instead_of_becoming_zero(self):
        actual = self.parse([command_event("readme", "cat README.md"), completed()])
        result = evaluate(load_case("non-ios-docs"), actual)
        self.assertEqual("pass", result["status"])
        self.assertEqual({"input_tokens": None, "cached_input_tokens": None, "output_tokens": None}, actual["usage"])
        self.assertEqual("unavailable_or_partial", result["token_status"])

    def test_multiple_turn_usage_is_summed_without_adding_cache_to_input(self):
        events = [{"type": "turn.started"}, command_event("same-id", "cat README.md"),
                  completed({"input_tokens": 100, "cached_input_tokens": 60, "output_tokens": 12}),
                  {"type": "turn.started"}, command_event("same-id", "cat .agents/skills/ios-workflow/SKILL.md"),
                  completed({"input_tokens": 80, "cached_input_tokens": 70, "output_tokens": 9})]
        actual = self.parse(events)
        self.assertEqual({"input_tokens": 180, "cached_input_tokens": 130, "output_tokens": 21}, actual["usage"])
        self.assertEqual(["SKILL.md"], [read["module"] for read in actual["reads"]])

    def test_started_and_completed_items_do_not_double_count(self):
        event = command_event("read", "cat .agents/skills/ios-workflow/SKILL.md")
        started = copy.deepcopy(event)
        started["type"] = "item.started"
        actual = self.parse([started, event, event, completed()])
        self.assertEqual(1, len(actual["reads"]))

    def test_invalid_token_types_and_duplicate_turns_are_not_fabricated_totals(self):
        actual = self.parse([completed({"input_tokens": True, "cached_input_tokens": -1, "output_tokens": "3"}), completed()])
        self.assertTrue(actual["parse_errors"])
        self.assertTrue(all(value is None for value in actual["usage"].values()))

    def test_reader_arguments_and_changed_working_directory_are_resolved(self):
        reads, unknown = command_reads("cd .agents/skills/ios-workflow && sed -n '1,90p' SKILL.md", self.project, self.skill)
        self.assertEqual(["SKILL.md"], reads)
        self.assertEqual([], unknown)
        reads, unknown = command_reads("head -n 12 .agents/skills/ios-workflow/references/standards/tracking-resume.md", self.project, self.skill)
        self.assertEqual(["references/standards/tracking-resume.md"], reads)
        self.assertEqual([], unknown)
        for command in ("cat .agents/skills/ios-workflow/references/*.md", "rg rule .agents/skills/ios-workflow/references", "rg rule"):
            self.assertTrue(command_reads(command, self.project, self.skill)[1])

    def test_conditional_or_redirected_reads_cannot_be_proved_by_aggregate_success(self):
        for command in ("false && cat .agents/skills/ios-workflow/SKILL.md || echo skipped",
                        "cat .agents/skills/ios-workflow/SKILL.md; echo done",
                        "cat .agents/skills/ios-workflow/SKILL.md | wc -l",
                        "cat .agents/skills/ios-workflow/SKILL.md > /dev/null",
                        "false\ncat .agents/skills/ios-workflow/SKILL.md"):
            result = evaluate(self.case, self.parse([command_event("conditional", command), completed()]))
            self.assertEqual([], result["loaded_modules"], command)
            self.assertEqual("inconclusive", result["status"], command)

    def test_instrumented_adapter_events_are_separate_from_native_shell_events(self):
        actual = self.parse([{"type": "module.read", "module": "SKILL.md"},
                             {"type": "module.read", "module": "references/standards/tracking-resume.md"}, completed()])
        self.assertEqual("pass", evaluate(self.case, actual)["status"])
        self.assertEqual({"instrumented"}, {read["source"] for read in actual["reads"]})

    def test_real_run_adapter_uses_default_model_read_only_and_ephemeral_isolation(self):
        def fake_run(command, **kwargs):
            self.assertNotIn("--model", command)
            self.assertNotIn("-m", command)
            self.assertNotIn("--ignore-user-config", command)
            self.assertEqual("read-only", command[command.index("--sandbox") + 1])
            self.assertIn("--ephemeral", command)
            self.assertIn("--json", command)
            kwargs["stdout"].write(json.dumps(completed({"input_tokens": 30, "cached_input_tokens": 20, "output_tokens": 4})) + "\n")
            return subprocess.CompletedProcess(command, 0)
        output = self.root / "run"
        with patch("evaluate_module_loading.shutil.which", return_value="/test/codex"), patch("evaluate_module_loading.subprocess.run", side_effect=fake_run):
            result = run_case(load_case("non-ios-docs"), output)
        self.assertEqual("pass", result["status"])
        self.assertTrue((output / "workspace/.agents/skills/ios-workflow/SKILL.md").is_file())
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertIsNone(manifest["model_override"])
        self.assertEqual(64, len(manifest["skill_snapshot_sha256"]))
        self.assertEqual(64, len(manifest["runner_sha256"]))
        with self.assertRaises(FileExistsError):
            run_case(load_case("non-ios-docs"), output)

    def test_timeout_is_an_incomplete_attempt_with_unknown_usage(self):
        with patch("evaluate_module_loading.shutil.which", return_value="/test/codex"), patch("evaluate_module_loading.subprocess.run", side_effect=subprocess.TimeoutExpired("codex", 1)):
            result = run_case(load_case("non-ios-docs"), self.root / "timed-out")
        self.assertEqual("inconclusive", result["status"])
        self.assertTrue(all(value is None for value in result["actual"]["usage"].values()))

    def test_run_refuses_runtime_records_inside_skill(self):
        with self.assertRaisesRegex(ValueError, "outside.*Skill"):
            run_case(load_case("non-ios-docs"), ROOT / ".agents/skills/ios-workflow/evaluation-must-not-exist")

    def test_import_refuses_output_inside_evaluated_skill(self):
        trace = self.root / "actual.jsonl"
        trace.write_text(json.dumps(completed()) + "\n")
        self.skill.mkdir(parents=True)
        output = self.skill / "evaluation.json"
        run = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/evaluate_module_loading.py"), "evaluate", "--case", "non-ios-docs", "--trace", str(trace),
                              "--project-root", str(self.project), "--output", str(output)], capture_output=True, text=True)
        self.assertNotEqual(0, run.returncode)
        self.assertIn("outside the distributed Skill", run.stderr)
        self.assertFalse(output.exists())

    def test_import_cli_executes_evaluation_without_launching_codex(self):
        trace = self.root / "actual.jsonl"
        trace.write_text(json.dumps(completed({"input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 1})) + "\n")
        output = self.root / "report.json"
        run = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/evaluate_module_loading.py"), "evaluate", "--case", "non-ios-docs", "--trace", str(trace),
                              "--project-root", str(self.project), "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertEqual("pass", json.loads(output.read_text())["status"])
        self.assertEqual("reported", json.loads(run.stdout)["token_status"])


if __name__ == "__main__":
    unittest.main()
