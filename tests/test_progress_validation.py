import copy
import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / ".agents/skills/ios-workflow"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from progress_validation import validate_progress


class ProgressValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.project = self.workspace / "device-one" / "Puzzle"
        files = {
            ".ios-workflow/sources/PRD.md": "# Memory Grid\nA completed round restores from local storage.\n",
            "App/MemoryGrid.swift": "struct MemoryGrid { var completed = false }\n",
            "project.yml": "name: Puzzle\n",
            ".ios-workflow/evidence/restore-test.txt": "Restore a completed round: passed\n",
        }
        for path, content in files.items():
            target = self.project / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        self.progress = {
            "schema_version": 1,
            "items": [{
                "id": "REQ-001-AC-001",
                "requirement_id": "REQ-001",
                "criterion": "A completed round restores from local storage after relaunch.",
                "source": {"path": ".ios-workflow/sources/PRD.md", "section": "Memory Grid"},
                "status": "verified",
                "implementation": ["App/MemoryGrid.swift"],
                "evidence": [{
                    "path": ".ios-workflow/evidence/restore-test.txt",
                    "sha256": self.digest(".ios-workflow/evidence/restore-test.txt"),
                    "inputs": [
                        {"path": path, "sha256": self.digest(path)}
                        for path in (".ios-workflow/sources/PRD.md", "App/MemoryGrid.swift", "project.yml")
                    ],
                    "environment": "fixture only; no simulator execution claimed",
                    "result": "passed",
                    "recorded_at": "2026-09-10T10:30:00+08:00",
                }],
            }],
        }

    def digest(self, path):
        return hashlib.sha256((self.project / path).read_bytes()).hexdigest()

    def errors(self):
        return validate_progress(self.project, self.progress)

    def test_progress_restores_at_a_different_absolute_project_path(self):
        other_device = self.workspace / "device-two" / "different-directory-name"
        shutil.copytree(self.project, other_device)
        shutil.rmtree(self.project)
        self.assertEqual([], validate_progress(other_device, self.progress))

    def test_missing_requirement_implementation_or_evidence_blocks_verified(self):
        for path in (".ios-workflow/sources/PRD.md", "App/MemoryGrid.swift",
                     ".ios-workflow/evidence/restore-test.txt"):
            with self.subTest(path=path):
                target = self.project / path
                content = target.read_bytes()
                target.unlink()
                self.assertTrue(self.errors())
                target.write_bytes(content)

    def test_changed_evidence_source_implementation_and_registered_build_inputs_block_reuse(self):
        for path in (".ios-workflow/evidence/restore-test.txt", ".ios-workflow/sources/PRD.md",
                     "App/MemoryGrid.swift", "project.yml"):
            with self.subTest(path=path):
                target = self.project / path
                content = target.read_bytes()
                target.write_bytes(content + b"changed\n")
                self.assertTrue(any("sha256" in error for error in self.errors()))
                target.write_bytes(content)

    def test_unrelated_document_changes_do_not_invalidate_registered_evidence(self):
        (self.project / "README.md").write_text("A new device can resume using project-relative paths.")
        self.assertEqual([], self.errors())

    def test_verified_requires_source_implementation_and_evidence(self):
        for field, value in (("source", {}), ("implementation", []), ("evidence", [])):
            with self.subTest(field=field):
                progress = copy.deepcopy(self.progress)
                progress["items"][0][field] = value
                self.assertTrue(validate_progress(self.project, progress))

    def test_implemented_is_distinct_from_verified(self):
        item = self.progress["items"][0]
        item["status"] = "implemented"
        item["evidence"] = []
        self.assertEqual([], self.errors())
        item["status"] = "verified"
        self.assertTrue(self.errors())

    def test_pending_does_not_claim_implementation_or_execution(self):
        item = self.progress["items"][0]
        item["status"] = "pending"
        item["implementation"] = []
        item["evidence"] = []
        self.assertEqual([], self.errors())

    def test_every_status_requires_requirement_id_and_criterion(self):
        for status in ("pending", "in_progress", "implemented", "verified", "blocked", "deferred", "cancelled"):
            for field in ("requirement_id", "criterion"):
                for value in (None, "", " \t\n", [], {}, 42):
                    with self.subTest(status=status, field=field, value=value):
                        progress = copy.deepcopy(self.progress)
                        item = progress["items"][0]
                        item["status"] = status
                        if value is None:
                            del item[field]
                        else:
                            item[field] = value
                        errors = validate_progress(self.project, progress)
                        self.assertTrue(any(f".{field}: 待补充" in error for error in errors))

    def test_evidence_requires_nonempty_environment(self):
        for value in (None, "", " \t\n", [], {}, 42):
            with self.subTest(value=value):
                progress = copy.deepcopy(self.progress)
                evidence = progress["items"][0]["evidence"][0]
                if value is None:
                    del evidence["environment"]
                else:
                    evidence["environment"] = value
                self.assertTrue(any(".environment: 待补证" in error
                                    for error in validate_progress(self.project, progress)))

    def test_evidence_result_is_required_and_has_a_fixed_vocabulary(self):
        for value in (None, "", "success", "PASSED", " passed ", [], {}, True):
            with self.subTest(value=value):
                progress = copy.deepcopy(self.progress)
                evidence = progress["items"][0]["evidence"][0]
                if value is None:
                    del evidence["result"]
                else:
                    evidence["result"] = value
                self.assertTrue(any(".result: 待补证" in error
                                    for error in validate_progress(self.project, progress)))

    def test_verified_rejects_failed_blocked_or_skipped_current_evidence(self):
        for result in ("failed", "blocked", "skipped"):
            with self.subTest(result=result):
                evidence = self.progress["items"][0]["evidence"][0]
                evidence["result"] = result
                self.assertTrue(any("verified 的当前证据必须为 passed" in error for error in self.errors()))

    def test_verified_rejects_one_failed_record_even_with_another_passing_record(self):
        failed = copy.deepcopy(self.progress["items"][0]["evidence"][0])
        failed["result"] = "failed"
        self.progress["items"][0]["evidence"].append(failed)
        self.assertTrue(any("evidence[1].result" in error for error in self.errors()))

    def test_incomplete_items_can_record_unsuccessful_evidence_without_becoming_verified(self):
        for status in ("pending", "in_progress", "implemented", "blocked", "deferred", "cancelled"):
            for result in ("passed", "failed", "blocked", "skipped"):
                with self.subTest(status=status, result=result):
                    item = self.progress["items"][0]
                    item["status"] = status
                    item["evidence"][0]["result"] = result
                    self.assertEqual([], self.errors())
                    self.assertEqual(status, item["status"])

    def test_recorded_at_accepts_valid_iso8601_timezone_forms(self):
        for timestamp in ("2026-09-10T02:30:00Z", "2026-09-10T10:30:00+08:00",
                          "2026-09-09T22:30:00.123456-04:00", "2026-09-10T10:30+0800",
                          "2024-02-29T10:30:00+08"):
            with self.subTest(timestamp=timestamp):
                self.progress["items"][0]["evidence"][0]["recorded_at"] = timestamp
                self.assertEqual([], self.errors())

    def test_recorded_at_rejects_missing_timezone_invalid_date_and_malformed_values(self):
        for value in (None, "", " \t", [], {}, 42, "yesterday", "2026-09-10",
                      "2026-09-10T10:30:00", "2026-09-10 10:30:00+08:00",
                      "2026-02-29T10:30:00Z", "2026-09-10T24:00:00Z",
                      "2026-09-10T10:30:00+24:00", "2026-09-10T10:30:00+08:99"):
            with self.subTest(value=value):
                progress = copy.deepcopy(self.progress)
                evidence = progress["items"][0]["evidence"][0]
                if value is None:
                    del evidence["recorded_at"]
                else:
                    evidence["recorded_at"] = value
                self.assertTrue(any(".recorded_at: 待补证" in error
                                    for error in validate_progress(self.project, progress)))

    def test_historical_missing_fields_report_all_errors_without_migration(self):
        item = self.progress["items"][0]
        del item["requirement_id"]
        del item["criterion"]
        for field in ("environment", "result", "recorded_at"):
            del item["evidence"][0][field]
        before = copy.deepcopy(self.progress)
        errors = self.errors()
        for field in ("requirement_id", "criterion", "environment", "result", "recorded_at"):
            self.assertTrue(any(f".{field}:" in error for error in errors))
        self.assertEqual(before, self.progress)

    def test_duplicate_ids_and_unknown_status_are_rejected(self):
        self.progress["items"].append(copy.deepcopy(self.progress["items"][0]))
        self.progress["items"][1]["status"] = "done"
        errors = self.errors()
        self.assertTrue(any("重复 ID" in error for error in errors))
        self.assertTrue(any("status" in error for error in errors))

    def test_verified_input_hashes_must_cover_source_and_implementation(self):
        evidence = self.progress["items"][0]["evidence"][0]
        for path in (".ios-workflow/sources/PRD.md", "App/MemoryGrid.swift"):
            with self.subTest(path=path):
                original = evidence["inputs"]
                evidence["inputs"] = [entry for entry in original if entry["path"] != path]
                self.assertTrue(any("未覆盖" in error for error in self.errors()))
                evidence["inputs"] = original

    def test_multiple_evidence_files_can_cover_different_inputs(self):
        first = self.progress["items"][0]["evidence"][0]
        second = copy.deepcopy(first)
        (self.project / ".ios-workflow/evidence/build-test.txt").write_text("Build fixture passed\n")
        second["path"] = ".ios-workflow/evidence/build-test.txt"
        second["sha256"] = self.digest(second["path"])
        second["inputs"] = first["inputs"][1:]
        first["inputs"] = first["inputs"][:1]
        self.progress["items"][0]["evidence"].append(second)
        self.assertEqual([], self.errors())

    def test_absolute_traversal_windows_paths_and_external_symlinks_are_rejected(self):
        outside = self.workspace / "outside.md"
        outside.write_text("external requirement")
        (self.project / "outside-link.md").symlink_to(outside)
        for path in (str(outside), "../../outside.md", "C:/external/PRD.md", "App\\PRD.md", "outside-link.md"):
            with self.subTest(path=path):
                progress = copy.deepcopy(self.progress)
                progress["items"][0]["source"]["path"] = path
                self.assertTrue(validate_progress(self.project, progress))

    def test_evidence_must_stay_in_project_records_directory(self):
        external_record = self.project / "test-result.txt"
        external_record.write_text("passed")
        linked_record = self.project / ".ios-workflow/evidence/link.txt"
        linked_record.symlink_to(external_record)
        for path in ("test-result.txt", ".ios-workflow/evidence/link.txt"):
            with self.subTest(path=path):
                evidence = self.progress["items"][0]["evidence"][0]
                evidence["path"] = path
                evidence["sha256"] = self.digest(path)
                self.assertTrue(self.errors())

    def test_skill_root_and_its_descendants_are_not_business_project_roots(self):
        for root in (SKILL_ROOT, SKILL_ROOT / "scripts"):
            with self.subTest(root=root):
                errors = validate_progress(root, self.progress)
                self.assertTrue(any("业务项目目录" in error for error in errors))

    def test_malformed_inputs_return_errors_instead_of_raising(self):
        for progress in (None, [], {}, {"schema_version": True, "items": []},
                         {"schema_version": 1, "items": [None]},
                         {"schema_version": 1, "items": [{"id": [], "status": {}, "source": {}}]}):
            with self.subTest(progress=progress):
                self.assertTrue(validate_progress(self.project, progress))
        for field, value in (("sha256", "abc"), ("inputs", []), ("inputs", [None]), ("environment", {})):
            with self.subTest(field=field, value=value):
                progress = copy.deepcopy(self.progress)
                progress["items"][0]["evidence"][0][field] = value
                self.assertTrue(validate_progress(self.project, progress))

    def test_validation_is_read_only_and_does_not_promote_status(self):
        before = copy.deepcopy(self.progress)
        files = {str(path.relative_to(self.project)): path.read_bytes()
                 for path in self.project.rglob("*") if path.is_file()}
        self.assertEqual([], self.errors())
        self.assertEqual(before, self.progress)
        self.assertEqual(files, {str(path.relative_to(self.project)): path.read_bytes()
                                 for path in self.project.rglob("*") if path.is_file()})


if __name__ == "__main__":
    unittest.main()
