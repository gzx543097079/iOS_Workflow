import copy
import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/ios-workflow/scripts"))
from tracking_state import validate_tracking_state
from resume_context import load_resume_context
from tests import test_resume_context as resume_fixture


class TrackingStateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = resume_fixture.ResumeContextTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.project = self.fixture.project
        self.archive = self.project / ".ios-workflow/requirements/REQ-current.md"

    def check(self, requirement_id="REQ-current"):
        return validate_tracking_state(self.project, requirement_id)

    def archive_header(self, *, status="in_progress", sequence="1", extra="", identifier="REQ-current", project="."):
        self.archive.write_text(f"---\nid: {identifier}\nproject: {project}\nsequence: {sequence}\nstatus: {status}\n"
                                f"{extra}---\nBody is not needed for metadata checks.\n")

    def done(self):
        self.fixture.index["active_requirement"] = None
        self.fixture.history["execution_order"][0]["status"] = "done"
        self.fixture.item["evidence"][0]["result"] = "passed"
        self.archive_header(status="done")
        self.fixture.save()

    def test_consistent_current_metadata_does_not_claim_business_verification(self):
        result = self.check()
        self.assertEqual([], result["errors"])
        self.assertTrue(result["metadata_only"])
        self.assertTrue(result["checked"])
        self.assertNotIn("verified", result)
        self.assertNotIn("passed", result)

    def test_completed_or_cancelled_active_requirement_is_reported(self):
        for status in ("done", "cancelled"):
            with self.subTest(status=status):
                self.fixture.index["active_requirement"]["status"] = status
                self.fixture.save()
                self.assertTrue(any("应清空活动索引" in error for error in self.check()["errors"]))
                self.assertTrue(load_resume_context(self.project)["errors"])

    def test_archive_id_project_status_and_sequence_must_match(self):
        for kwargs, field in (({"identifier": "REQ-wrong"}, "id"), ({"project": "other"}, "project"),
                              ({"status": "ready"}, "status"), ({"sequence": "2"}, "sequence")):
            with self.subTest(kwargs=kwargs):
                self.archive_header(**kwargs)
                self.assertTrue(any(f"requirement.{field}:" in error for error in self.check()["errors"]))

    def test_known_step_frontmatter_is_checked_but_legacy_body_steps_need_no_migration(self):
        self.assertEqual([], self.check()["errors"])
        self.archive_header(extra="current_step: STEP-999\n")
        self.assertTrue(any("current_step" in error for error in self.check()["errors"]))
        self.archive_header(extra="current_step: STEP-002\n")
        self.assertEqual([], self.check()["errors"])

    def test_missing_history_or_missing_executed_entry_is_reported(self):
        path = self.project / ".ios-workflow/history.jsonc"
        path.unlink()
        self.assertTrue(self.check()["errors"])
        self.fixture.history["execution_order"] = []
        self.fixture.save()
        self.assertTrue(any("缺少台账记录" in error for error in self.check()["errors"]))

    def test_unstarted_draft_can_have_null_sequence_without_history_entry(self):
        self.fixture.index["active_requirement"]["status"] = "draft"
        self.fixture.item["status"] = "pending"
        self.fixture.item["evidence"] = []
        self.fixture.item["implementation"] = []
        self.fixture.history.update(next_sequence=1, execution_order=[])
        self.fixture.save()
        self.archive_header(status="draft", sequence="null")
        self.assertEqual([], self.check()["errors"])

    def test_global_duplicate_history_ids_and_sequences_are_detected(self):
        original = copy.deepcopy(self.fixture.history["execution_order"][0])
        for changes, expected in (({}, "重复需求 ID"), ({"id": "OLD"}, "重复执行序号")):
            with self.subTest(changes=changes):
                duplicate = dict(original, **changes)
                self.fixture.history["execution_order"] = [original, duplicate]
                self.fixture.save()
                self.assertTrue(any(expected in error for error in self.check()["errors"]))

    def test_next_sequence_cannot_reuse_assigned_numbers(self):
        for value in (None, True, 0, 1, "2"):
            with self.subTest(value=value):
                self.fixture.history["next_sequence"] = value
                self.fixture.save()
                self.assertTrue(any("next_sequence" in error for error in self.check()["errors"]))

    def test_history_status_and_archive_path_disagreement_are_reported(self):
        self.fixture.history["execution_order"][0]["status"] = "done"
        self.fixture.save()
        self.assertTrue(any("档案与执行台账不一致" in error for error in self.check()["errors"]))
        other = self.project / ".ios-workflow/requirements/other.md"
        other.write_text(self.archive.read_text())
        self.fixture.history["execution_order"][0].update(status="in_progress", file=other.relative_to(self.project).as_posix())
        self.fixture.save()
        self.assertTrue(any("指向不同档案" in error for error in self.check()["errors"]))

    def test_done_cannot_hide_pending_items_outside_resume_page(self):
        self.done()
        for number in range(2, 23):
            item = copy.deepcopy(self.fixture.item)
            item["id"] = f"REQ-current-AC-{number:03}"
            self.fixture.progress["items"].append(item)
        self.fixture.progress["items"][-1]["status"] = "pending"
        self.fixture.save()
        result = load_resume_context(self.project, "REQ-current", max_items=1)
        self.assertTrue(result["has_more"])
        self.assertTrue(any("REQ-current-AC-022" in error and "pending" in error for error in result["errors"]))

    def test_done_cannot_claim_verified_with_missing_or_failed_recorded_evidence(self):
        self.done()
        for evidence in ([], [None], [{"result": "failed"}], [{"result": "skipped"}]):
            with self.subTest(evidence=evidence):
                self.fixture.item["evidence"] = evidence
                self.fixture.save()
                self.assertTrue(any("登记的成功证据" in error for error in self.check()["errors"]))

    def test_deferred_and_cancelled_items_need_source_and_reason(self):
        self.done()
        for status in ("deferred", "cancelled"):
            self.fixture.item["status"] = status
            for decision in (None, {}, {"reason": "Approved later"},
                             {"reason": "Approved later", "source": {"path": "missing.md", "section": "Decision"}}):
                with self.subTest(status=status, decision=decision):
                    self.fixture.item["scope_decision"] = decision
                    self.fixture.save()
                    self.assertTrue(any("scope_decision" in error for error in self.check()["errors"]))
        self.fixture.item["scope_decision"] = {
            "reason": "Deferred by the recorded scope decision",
            "source": {"path": ".ios-workflow/sources/PRD.md", "section": "Scope decision"},
        }
        self.fixture.save()
        self.assertEqual([], self.check()["errors"])

    def test_unrelated_archives_and_evidence_are_not_opened(self):
        self.fixture.history["execution_order"].append({"id": "OLD", "sequence": 2, "status": "done",
                                                       "file": ".ios-workflow/requirements/missing-old.md"})
        self.fixture.history["next_sequence"] = 3
        self.fixture.progress["items"].append({"id": "OLD-AC", "requirement_id": "OLD", "status": "verified",
                                               "evidence": [{"path": "missing-old-report"}]})
        self.fixture.save()
        allowed = {self.archive, *(self.project / ".ios-workflow" / name
                                  for name in ("index.jsonc", "progress.json", "history.jsonc"))}
        allowed = {path.resolve() for path in allowed}
        original = Path.open

        def guarded(path, *args, **kwargs):
            self.assertIn(path, allowed)
            return original(path, *args, **kwargs)

        with patch.object(Path, "open", guarded):
            self.assertEqual([], self.check()["errors"])

    def test_frontmatter_scalar_subset_accepts_legacy_values_and_ignores_body(self):
        self.archive_header(extra='design_level: null\nbranch: ""\ncreated_at: 2026-09-10 10:00 +0800\n'
                                  'title: "a: b"\nnotes: \'user\'\'s choice\'\n')
        with self.archive.open("ab") as stream:
            stream.write(b"\xff invalid UTF-8 body must not be decoded")
        self.assertEqual([], self.check()["errors"])

    def test_complex_or_duplicate_frontmatter_is_rejected_instead_of_guessed(self):
        for extra in ("status: done\n", "notes:\n  nested: value\n", "notes: |\n  details\n",
                      "notes: [a, b]\n", "notes: &alias value\n", "notes: value # comment\n"):
            with self.subTest(extra=extra):
                self.archive_header(extra=extra)
                self.assertTrue(any("frontmatter" in error for error in self.check()["errors"]))

    def test_frontmatter_size_and_termination_are_checked(self):
        for content in ("no frontmatter", "---\nid: REQ-current\n", "---\nnotes: " + "a" * 66000):
            with self.subTest(length=len(content)):
                self.archive.write_text(content)
                self.assertTrue(any("frontmatter" in error for error in self.check()["errors"]))

    def test_bad_json_and_deep_json_return_errors(self):
        for name in ("index.jsonc", "progress.json", "history.jsonc"):
            for content in ("not json", '{"nested":' + '[' * 1100 + '0' + ']' * 1100 + '}'):
                with self.subTest(name=name, deep=len(content) > 100):
                    self.fixture.save()
                    (self.project / ".ios-workflow" / name).write_text(content)
                    self.assertTrue(self.check()["errors"])

    def test_archive_symlink_escape_is_rejected(self):
        external = Path(self.fixture.temp.name) / "outside.md"
        self.archive.rename(external)
        self.archive.symlink_to(external)
        self.assertTrue(any("越过项目目录" in error for error in self.check()["errors"]))

    def test_no_active_selection_does_not_claim_every_requirement_done(self):
        self.fixture.index["active_requirement"] = None
        self.fixture.save()
        result = self.check(None)
        self.assertEqual([], result["errors"])
        self.assertFalse(result["checked"])
        self.assertIsNone(result["requirement_id"])

    def test_different_device_path_and_read_only_behavior(self):
        before = {path.relative_to(self.project): path.read_bytes() for path in self.project.rglob("*") if path.is_file()}
        expected = self.check()
        self.assertEqual(before, {path.relative_to(self.project): path.read_bytes()
                                  for path in self.project.rglob("*") if path.is_file()})
        moved = Path(self.fixture.temp.name) / "second-device" / "DifferentName"
        shutil.copytree(self.project, moved)
        shutil.rmtree(self.project)
        self.assertEqual(expected, validate_tracking_state(moved, "REQ-current"))


if __name__ == "__main__":
    unittest.main()
