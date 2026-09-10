import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / ".agents/skills/ios-workflow"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from resume_context import load_resume_context


class ResumeContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "first-device" / "Project"
        self.project.mkdir(parents=True)
        self.index = {
            "version": 3, "last_requirement_id": "REQ-current",
            "active_requirement": {
                "id": "REQ-current", "project": ".",
                "file": ".ios-workflow/requirements/REQ-current.md",
                "title": "Restore a round", "status": "in_progress",
                "current_step": "STEP-002", "next_action": "Run restore tests",
                "blockers": ["Simulator unavailable"], "evidence_key": "unknown",
                "scope_version": 1, "branch": "feature/restore",
                "observed_head": "abc123", "updated_at": "2026-09-10 10:00 +0800",
            },
        }
        self.item = {
            "id": "REQ-current-AC-001", "requirement_id": "REQ-current",
            "criterion": "Opening a saved round restores the board",
            "source": {"path": ".ios-workflow/sources/PRD.md", "section": "Restore"},
            "status": "verified", "implementation": ["App/Restore.swift"],
            "evidence": [{"path": ".ios-workflow/evidence/result.txt", "sha256": "old",
                          "inputs": [{"path": "old", "sha256": "old"}]}],
        }
        self.progress = {"schema_version": 1, "items": [self.item]}
        for relative in (".ios-workflow/requirements/REQ-current.md", ".ios-workflow/sources/PRD.md",
                         ".ios-workflow/handoff.md", ".ios-workflow/evidence/result.txt", "App/Restore.swift"):
            target = self.project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("Do not read file content during summary extraction", encoding="utf-8")
        self.save()

    def save(self):
        (self.project / ".ios-workflow/index.jsonc").write_text("// Project activity\n" + json.dumps(self.index))
        (self.project / ".ios-workflow/progress.json").write_text(json.dumps(self.progress))

    def test_selects_current_requirement_and_returns_only_recorded_metadata(self):
        result = load_resume_context(self.project)
        self.assertEqual([], result["errors"])
        self.assertTrue(result["metadata_only"])
        self.assertEqual("REQ-current", result["requirement_id"])
        self.assertEqual("verified", result["items"][0]["recorded_status"])
        self.assertNotIn("status", result["items"][0])
        self.assertNotIn("evidence", result["items"][0])
        self.assertNotIn("implementation", result["items"][0])
        self.assertEqual(1, result["items"][0]["evidence_count"])
        self.assertEqual("Run restore tests", result["next_action"])
        self.assertIn("Simulator unavailable", result["blockers"])
        self.assertIn(".ios-workflow/requirements/REQ-current.md", result["required_files"])
        self.assertIn(".ios-workflow/handoff.md", result["required_files"])
        self.assertNotIn("complete", result)

    def test_reads_only_index_and_progress_and_does_not_write(self):
        before = {str(p.relative_to(self.project)): p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        original = Path.read_text
        reads = []

        def checked_read(path, *args, **kwargs):
            relative = str(path.relative_to(self.project.resolve()))
            self.assertIn(relative, {".ios-workflow/index.jsonc", ".ios-workflow/progress.json"})
            reads.append(relative)
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", checked_read):
            self.assertEqual([], load_resume_context(self.project)["errors"])
        self.assertEqual(2, len(reads))
        self.assertEqual(before, {str(p.relative_to(self.project)): p.read_bytes() for p in self.project.rglob("*") if p.is_file()})

    def test_hundreds_of_unrelated_history_items_are_not_inspected_or_returned(self):
        for number in range(400):
            self.progress["items"].append({"id": f"OLD-{number}", "requirement_id": f"OLD-{number}",
                                           "evidence": [{"path": "/unavailable-device/result"}]})
        self.save()
        result = load_resume_context(self.project)
        self.assertEqual([], result["errors"])
        self.assertEqual(1, result["total_items"])
        self.assertEqual(1, len(result["items"]))
        self.assertNotIn("OLD-", json.dumps(result))

    def test_long_summary_text_and_blocker_lists_report_truncation(self):
        self.item["criterion"] = "criterion " * 1000
        active = self.index["active_requirement"]
        active["next_action"] = "next action " * 1000
        active["blockers"] = ["blocked " * 1000 for _ in range(100)]
        self.save()
        result = load_resume_context(self.project)
        self.assertEqual([], result["errors"])
        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(result["items"][0]["criterion"]), 800)
        self.assertLessEqual(len(result["next_action"]), 800)
        self.assertEqual(20, len(result["blockers"]))
        self.assertTrue(all(len(value) <= 800 for value in result["blockers"]))
        self.assertEqual(80, result["omitted"]["blockers"])
        self.assertIn("progress.items[0].criterion", result["truncated_fields"])
        self.assertIn("index.active_requirement.next_action", result["truncated_fields"])

    def test_hundreds_of_metadata_errors_are_counted_without_full_output(self):
        self.progress["items"].extend([None] * 400)
        self.save()
        result = load_resume_context(self.project)
        self.assertEqual(400, result["error_count"])
        self.assertEqual(50, len(result["errors"]))
        self.assertEqual(350, result["omitted"]["errors"])
        self.assertTrue(result["truncated"])

    def test_oversized_ids_and_paths_are_rejected_instead_of_shortened(self):
        long_id = "requirement-" * 1000
        result = load_resume_context(self.project, long_id)
        self.assertTrue(result["errors"])
        self.assertIsNone(result["requirement_id"])
        self.assertNotIn(long_id[:256], json.dumps(result))
        self.item["id"] = long_id
        self.item["source"]["path"] = ".ios-workflow/" + "long-path/" * 1000
        self.save()
        result = load_resume_context(self.project)
        self.assertTrue(result["errors"])
        self.assertIsNone(result["items"][0]["id"])
        self.assertNotIn("source", result["items"][0])
        self.assertNotIn("long-path/", json.dumps(result))

    def test_explicit_requirement_selection_and_pagination(self):
        for number in range(25):
            item = copy.deepcopy(self.item)
            item.update(id=f"REQ-other-AC-{number:03}", requirement_id="REQ-other")
            self.progress["items"].append(item)
        self.save()
        result = load_resume_context(self.project, "REQ-other", max_items=10, offset=10)
        self.assertEqual([], result["errors"])
        self.assertEqual(25, result["total_items"])
        self.assertEqual(10, len(result["items"]))
        self.assertTrue(result["has_more"])
        self.assertEqual("REQ-other-AC-010", result["items"][0]["id"])
        self.assertIsNone(result["active_requirement"])
        self.assertIsNone(result["next_action"])
        last = load_resume_context(self.project, "REQ-other", max_items=10, offset=20)
        self.assertEqual(5, len(last["items"]))
        self.assertFalse(last["has_more"])
        beyond = load_resume_context(self.project, "REQ-other", offset=100)
        self.assertEqual([], beyond["items"])
        self.assertEqual(25, beyond["total_items"])

    def test_empty_active_index_and_unknown_explicit_requirement(self):
        self.index["active_requirement"] = None
        self.save()
        result = load_resume_context(self.project)
        self.assertEqual([], result["errors"])
        self.assertIsNone(result["requirement_id"])
        self.assertEqual([], result["items"])
        self.assertEqual([], load_resume_context(self.project, "REQ-current")["errors"])
        self.assertTrue(load_resume_context(self.project, "REQ-unknown")["errors"])

    def test_invalid_pagination_and_requirement_selection_return_errors(self):
        for arguments in ({"max_items": 0}, {"max_items": 101}, {"max_items": True}, {"max_items": "20"},
                          {"offset": -1}, {"offset": False}, {"offset": 1.5}, {"requirement_id": []},
                          {"requirement_id": " "}):
            with self.subTest(arguments=arguments):
                self.assertTrue(load_resume_context(self.project, **arguments)["errors"])

    def test_duplicate_ids_even_across_pages_are_reported(self):
        self.progress["items"].append(copy.deepcopy(self.item))
        self.save()
        result = load_resume_context(self.project, max_items=1)
        self.assertTrue(any("重复" in error for error in result["errors"]))

    def test_malformed_selected_metadata_does_not_appear_valid(self):
        original = copy.deepcopy(self.item)
        for field, value in (("requirement_id", None), ("criterion", ""), ("status", []),
                             ("source", None), ("implementation", []), ("evidence", []),
                             ("evidence", [None])):
            with self.subTest(field=field):
                self.progress["items"] = [dict(original, **{field: value})]
                self.save()
                self.assertTrue(load_resume_context(self.project)["errors"])

    def test_missing_or_invalid_record_files_are_reported(self):
        for relative, content in (("index.jsonc", "not json"), ("progress.json", "[]"),
                                  ("index.jsonc", '{"version": 3}'),
                                  ("progress.json", '{"schema_version": 2, "items": []}')):
            with self.subTest(relative=relative, content=content):
                self.save()
                (self.project / ".ios-workflow" / relative).write_text(content)
                self.assertTrue(load_resume_context(self.project)["errors"])
        self.save()
        (self.project / ".ios-workflow/index.jsonc").unlink()
        self.assertTrue(load_resume_context(self.project)["errors"])

    def test_missing_references_and_unsafe_paths_are_reported_without_reading(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("external")
        (self.project / "outside-link").symlink_to(outside)
        for reference in (str(outside), "../outside.txt", "C:/outside.txt", "App\\Restore.swift", "outside-link", "missing.swift"):
            with self.subTest(reference=reference):
                self.item["implementation"] = [reference]
                self.save()
                self.assertTrue(load_resume_context(self.project)["errors"])
        self.item["implementation"] = ["App/Restore.swift"]
        self.item["source"]["path"] = str(outside)
        self.save()
        result = load_resume_context(self.project)
        self.assertTrue(result["errors"])
        self.assertNotIn(str(outside), json.dumps(result))

    def test_record_file_symlink_cannot_escape_project(self):
        record = self.project / ".ios-workflow/progress.json"
        outside = Path(self.temp.name) / "outside.json"
        record.rename(outside)
        record.symlink_to(outside)
        result = load_resume_context(self.project)
        self.assertTrue(result["errors"])
        self.assertEqual([], result["items"])

    def test_restores_under_a_different_absolute_path(self):
        other = Path(self.temp.name) / "second-device" / "Renamed"
        shutil.copytree(self.project, other)
        expected = load_resume_context(self.project)
        shutil.rmtree(self.project)
        self.assertEqual(expected, load_resume_context(other))

    def test_invalid_roots_are_reported(self):
        for root in (None, self.project / "missing", self.project / ".ios-workflow/progress.json", SKILL_ROOT):
            with self.subTest(root=root):
                self.assertTrue(load_resume_context(root)["errors"])
