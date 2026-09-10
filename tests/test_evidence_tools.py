import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / ".agents/skills/ios-workflow"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from evidence_tools import ENVIRONMENT_FIELDS, capture_evidence, compare_evidence
from progress_validation import validate_progress


class EvidenceToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.project = self.workspace / "device-one" / "Puzzle"
        self.files = {
            ".ios-workflow/sources/PRD.md": "# Restore\nA completed round restores after relaunch.\n",
            "App/Game.swift": "struct Game { var completed = false }\n",
            "project.yml": "name: Puzzle\n",
            ".ios-workflow/evidence/restore.txt": "Fixture only: RestoreTests passed; no simulator was run.\n",
        }
        for name, content in self.files.items():
            path = self.project / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.inputs = [".ios-workflow/sources/PRD.md", "App/Game.swift", "project.yml"]
        self.evidence = ".ios-workflow/evidence/restore.txt"
        self.environment = {
            "xcode": "fixture-xcode-16.4",
            "sdk": "fixture-iphonesimulator18.5",
            "scheme": "Puzzle",
            "configuration": "Debug",
            "destination": "fixture iPhone 16, iOS 18.5; no simulator execution claimed",
            "test_selection": ["PuzzleTests/RestoreTests/testCompletedRound"],
        }
        self.record = self.capture()

    def capture(self, **overrides):
        arguments = {
            "project_root": self.project,
            "evidence_path": self.evidence,
            "input_paths": self.inputs,
            "environment": self.environment,
            "result": "passed",
            "recorded_at": "2026-09-10T10:00:00+08:00",
        }
        arguments.update(overrides)
        return capture_evidence(**arguments)

    def compare(self, **overrides):
        arguments = {
            "project_root": self.project,
            "record": self.record,
            "current_environment": self.environment,
            "current_input_paths": self.inputs,
        }
        arguments.update(overrides)
        return compare_evidence(**arguments)

    def test_capture_hashes_actual_files_and_complete_environment(self):
        record = self.record
        self.assertEqual(hashlib.sha256((self.project / self.evidence).read_bytes()).hexdigest(), record["sha256"])
        self.assertEqual(sorted(self.inputs), [entry["path"] for entry in record["inputs"]])
        for entry in record["inputs"]:
            self.assertEqual(hashlib.sha256((self.project / entry["path"]).read_bytes()).hexdigest(), entry["sha256"])
        values = record["environment_fingerprint"]["values"]
        canonical = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), record["environment_fingerprint"]["sha256"])
        self.assertTrue(all(field in record["environment"] for field in ENVIRONMENT_FIELDS))
        self.assertEqual({"status": "matched", "reasons": []}, self.compare())

    def test_capture_uses_current_timezone_aware_time_when_omitted(self):
        record = self.capture(recorded_at=None)
        self.assertIsNotNone(datetime.fromisoformat(record["recorded_at"]).utcoffset())

    def test_capture_rejects_invalid_result_time_or_empty_input_set(self):
        for values in ({"result": "success"}, {"result": []}, {"recorded_at": "2026-09-10"},
                       {"recorded_at": "2026-09-10T10:00:00"}, {"input_paths": []}, {"input_paths": None}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.capture(**values)

    def test_capture_rejects_missing_or_unknown_required_environment_values(self):
        for field in ENVIRONMENT_FIELDS:
            for value in (None, "", " \t", "unknown", "incomplete", "待补充", {}):
                with self.subTest(field=field, value=value):
                    environment = copy.deepcopy(self.environment)
                    if value is None:
                        del environment[field]
                    else:
                        environment[field] = value
                    with self.assertRaisesRegex(ValueError, field):
                        self.capture(environment=environment)
                    self.assertEqual("unknown", self.compare(current_environment=environment)["status"])

    def test_environment_change_invalidates_reuse_for_each_required_dimension(self):
        for field in ENVIRONMENT_FIELDS:
            with self.subTest(field=field):
                environment = copy.deepcopy(self.environment)
                environment[field] = "changed fixture"
                result = self.compare(current_environment=environment)
                self.assertEqual("stale", result["status"])
                self.assertTrue(any("当前环境" in reason for reason in result["reasons"]))

    def test_extra_environment_dimension_participates_in_fingerprint(self):
        self.environment["macos"] = "fixture-15.5"
        self.record = self.capture()
        self.environment["macos"] = "fixture-15.6"
        self.assertEqual("stale", self.compare()["status"])

    def test_environment_key_and_test_selection_order_do_not_change_fingerprint(self):
        self.environment["test_selection"] = ["PuzzleTests/B", "PuzzleTests/A"]
        self.record = self.capture()
        reordered = dict(reversed(list(self.environment.items())))
        reordered["test_selection"] = ["PuzzleTests/A", "PuzzleTests/B", "PuzzleTests/A"]
        self.assertEqual("matched", self.compare(current_environment=reordered)["status"])

    def test_string_test_selection_is_supported(self):
        self.environment["test_selection"] = "PuzzleTests/RestoreTests"
        self.record = self.capture()
        self.assertEqual("matched", self.compare()["status"])

    def test_changed_input_or_evidence_bytes_invalidate_reuse(self):
        for name in self.inputs + [self.evidence]:
            with self.subTest(name=name):
                path = self.project / name
                before = path.read_bytes()
                path.write_bytes(before + b"changed\n")
                result = self.compare()
                self.assertEqual("stale", result["status"])
                self.assertTrue(any("文件已变化" in reason for reason in result["reasons"]))
                path.write_bytes(before)

    def test_new_or_removed_explicit_input_invalidates_reuse(self):
        (self.project / "Package.resolved").write_text("fixture dependency lock\n")
        for inputs in (self.inputs + ["Package.resolved"], self.inputs[:-1]):
            with self.subTest(inputs=inputs):
                result = self.compare(current_input_paths=inputs)
                self.assertEqual("stale", result["status"])
                self.assertTrue(any("输入集合已变化" in reason for reason in result["reasons"]))

    def test_missing_file_is_unknown_instead_of_success(self):
        for name in self.inputs + [self.evidence]:
            with self.subTest(name=name):
                path = self.project / name
                before = path.read_bytes()
                path.unlink()
                self.assertEqual("unknown", self.compare()["status"])
                with self.assertRaises(ValueError):
                    self.capture()
                path.write_bytes(before)

    def test_failed_blocked_and_skipped_results_cannot_match(self):
        for result in ("failed", "blocked", "skipped"):
            with self.subTest(result=result):
                record = self.capture(result=result)
                comparison = self.compare(record=record)
                self.assertEqual("stale", comparison["status"])
                self.assertTrue(any(result in reason for reason in comparison["reasons"]))

    def test_historical_missing_fields_are_unknown_without_mutation(self):
        for field in ("path", "sha256", "inputs", "environment", "environment_fingerprint", "result", "recorded_at"):
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                del record[field]
                before = copy.deepcopy(record)
                self.assertEqual("unknown", self.compare(record=record)["status"])
                self.assertEqual(before, record)

    def test_malformed_records_return_unknown_without_raising(self):
        for record in (None, [], {}, {"result": []}, {"environment_fingerprint": []}):
            with self.subTest(record=record):
                self.assertEqual("unknown", self.compare(record=record)["status"])
        for field, value in (("inputs", []), ("inputs", [None]), ("sha256", "abc"),
                             ("environment_fingerprint", {"schema_version": True}),
                             ("environment", {}), ("recorded_at", {})):
            with self.subTest(field=field, value=value):
                record = copy.deepcopy(self.record)
                record[field] = value
                self.assertEqual("unknown", self.compare(record=record)["status"])
        self.assertEqual("unknown", self.compare(current_input_paths=[])["status"])
        self.assertEqual("unknown", self.compare(current_environment=None)["status"])

    def test_corrupt_or_missing_fingerprint_is_not_reusable(self):
        for field in ("sha256", "values"):
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                del record["environment_fingerprint"][field]
                self.assertEqual("unknown", self.compare(record=record)["status"])
        self.record["environment_fingerprint"]["values"]["xcode"] = "tampered fixture"
        self.assertEqual("stale", self.compare()["status"])

    def test_unsafe_paths_and_evidence_outside_records_directory_are_rejected(self):
        outside = self.workspace / "outside.txt"
        outside.write_text("external fixture")
        (self.project / "external-link.txt").symlink_to(outside)
        (self.project / ".ios-workflow/evidence/external-link.txt").symlink_to(outside)
        for path in (str(outside), "../../outside.txt", "C:/external.txt", "App\\Game.swift", "external-link.txt"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    self.capture(input_paths=[path])
                self.assertEqual("unknown", self.compare(current_input_paths=[path])["status"])
        for path in ("App/Game.swift", ".ios-workflow/evidence/external-link.txt"):
            with self.subTest(evidence_path=path), self.assertRaises(ValueError):
                self.capture(evidence_path=path)

    def test_skill_root_or_descendants_cannot_be_project_roots(self):
        for root in (SKILL_ROOT, SKILL_ROOT / "scripts"):
            with self.subTest(root=root):
                with self.assertRaises(ValueError):
                    self.capture(project_root=root)
                self.assertEqual("unknown", self.compare(project_root=root)["status"])

    def test_record_restores_at_different_absolute_path(self):
        other_device = self.workspace / "device-two" / "renamed-checkout"
        shutil.copytree(self.project, other_device)
        shutil.rmtree(self.project)
        self.assertEqual("matched", self.compare(project_root=other_device)["status"])

    def test_unrelated_document_change_does_not_invalidate_reuse(self):
        (self.project / "README.md").write_text("New checkout instructions.\n")
        self.assertEqual("matched", self.compare()["status"])

    def test_capture_and_compare_are_read_only_and_keep_progress_contract(self):
        inputs_before = copy.deepcopy(self.inputs)
        environment_before = copy.deepcopy(self.environment)
        record_before = copy.deepcopy(self.record)
        files_before = {path.relative_to(self.project): path.read_bytes()
                        for path in self.project.rglob("*") if path.is_file()}
        self.capture()
        self.compare()
        progress = {"schema_version": 1, "items": [{
            "id": "REQ-001-AC-001", "requirement_id": "REQ-001", "criterion": "Completed rounds restore.",
            "source": {"path": self.inputs[0], "section": "Restore"}, "status": "verified",
            "implementation": ["App/Game.swift"], "evidence": [self.record],
        }]}
        self.assertEqual([], validate_progress(self.project, progress))
        self.assertEqual(inputs_before, self.inputs)
        self.assertEqual(environment_before, self.environment)
        self.assertEqual(record_before, self.record)
        self.assertEqual(files_before, {path.relative_to(self.project): path.read_bytes()
                                       for path in self.project.rglob("*") if path.is_file()})


if __name__ == "__main__":
    unittest.main()
