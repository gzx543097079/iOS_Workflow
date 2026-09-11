import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/ios-workflow/scripts"))
from tracking_patch import read_tracking_snapshot, prepare_tracking_patch
from tracking_update import TrackingUpdateError, apply_tracking_update, recover_tracking_update
from resume_context import load_resume_context
from tests import test_tracking_update as fixtures


class TrackingPatchTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TrackingUpdateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.project
        self.req = self.fixture.requirement_id
        self.item = self.fixture.progress["items"][0]["id"]

    def prepare(self, updates, hashes=None):
        if hashes is None:
            hashes = read_tracking_snapshot(self.root, self.req)["expected_hashes"]
        return prepare_tracking_patch(self.root, self.req, updates, hashes)

    def test_snapshot_returns_versions_without_record_bodies(self):
        result = read_tracking_snapshot(self.root, self.req)
        self.assertEqual(self.fixture.expected, result["expected_hashes"])
        self.assertNotIn("Original notes", json.dumps(result))
        self.assertNotIn("items", result)

    def test_local_merge_preserves_unrelated_items_and_original_archive_body(self):
        progress = copy.deepcopy(self.fixture.progress)
        other = copy.deepcopy(progress["items"][0])
        other.update(id="OTHER-AC", requirement_id="REQ-OTHER")
        progress["items"].append(other)
        self.fixture.install_old_document(".ios-workflow/progress.json", progress)
        updates = {"items": [{"id": self.item, "set": {"status": "implemented", "evidence": []}}],
                   "active_requirement": {"next_action": "运行受影响测试"},
                   "archive": {"append": "本阶段已实现，尚未验证。"}}
        request_before = copy.deepcopy(updates)
        result = self.prepare(updates)
        self.assertEqual(self.fixture.original, self.fixture.targets(), "prepare cannot change live records")
        apply_tracking_update(self.root, result["transaction_id"])
        saved = json.loads((self.root / ".ios-workflow/progress.json").read_text())
        self.assertEqual(other, saved["items"][1])
        self.assertEqual("implemented", saved["items"][0]["status"])
        self.assertEqual(updates, request_before)
        self.assertIn("Original notes\n本阶段", (self.root / self.fixture.archive).read_text())

    def test_external_edit_since_snapshot_is_rejected_without_rebasing(self):
        hashes = read_tracking_snapshot(self.root, self.req)["expected_hashes"]
        archive = self.root / self.fixture.archive
        archive.write_text(archive.read_text() + "External change\n")
        before = self.fixture.targets()
        with self.assertRaises(TrackingUpdateError):
            self.prepare({"archive": {"append": "New notes"}}, hashes)
        self.assertEqual(before, self.fixture.targets())

    def test_failed_result_cannot_be_promoted_to_verified(self):
        evidence = copy.deepcopy(self.fixture.progress["items"][0]["evidence"])
        evidence[0]["result"] = "failed"
        with self.assertRaises(TrackingUpdateError):
            self.prepare({"items": [{"id": self.item, "set": {"status": "verified", "evidence": evidence}}]})
        self.assertEqual(self.fixture.original, self.fixture.targets())

    def test_terminal_state_must_be_explicit_and_consistent_in_all_records(self):
        with self.assertRaises(TrackingUpdateError):
            self.prepare({"history_entry": {"status": "done"}})
        result = self.prepare({"history_entry": {"status": "done"}, "active_requirement": None,
                               "archive": {"metadata": {"status": "done"}, "append": "本次验收结束。"}})
        apply_tracking_update(self.root, result["transaction_id"])
        self.assertEqual("done", read_tracking_snapshot(self.root, self.req)["recorded_status"])

    def test_cannot_reassign_identifiers_sequences_or_unknown_items(self):
        for update in ({"history_entry": {"sequence": 99}}, {"archive": {"metadata": {"id": "OTHER"}}},
                       {"active_requirement": {"file": "outside.md"}},
                       {"items": [{"id": self.item, "set": {"requirement_id": "OTHER"}}]},
                       {"items": [{"id": "UNKNOWN", "set": {"status": "verified"}}]}):
            with self.subTest(update=update), self.assertRaises(TrackingUpdateError):
                self.prepare(update)
        self.assertEqual(self.fixture.original, self.fixture.targets())

    def test_unknown_new_fields_are_rejected_in_every_update_location(self):
        for update in (
                {"items": [{"id": self.item, "set": {"stauts": "implemented"}}]},
                {"active_requirement": {"next_acton": "Run tests"}},
                {"history_entry": {"stauts": "done"}},
                {"archive": {"metadata": {"stauts": "done"}}},
                {"items": [{"id": self.item, "set": {"new_custom_field": "new"}}]}):
            with self.subTest(update=update), self.assertRaisesRegex(TrackingUpdateError, "未知字段"):
                self.prepare(update)
        self.assertEqual(self.fixture.original, self.fixture.targets())
        self.assertFalse((self.root / ".ios-workflow/transactions").exists())

    def test_existing_extension_fields_remain_editable_and_archive_body_is_preserved(self):
        progress = copy.deepcopy(self.fixture.progress)
        progress["items"][0]["team_note"] = "Previous team observation"
        self.fixture.install_old_document(".ios-workflow/progress.json", progress)
        archive = self.root / self.fixture.archive
        archive.write_text(archive.read_text().replace("id: REQ-001\n", 'id: REQ-001\nteam_note: "Previous"\n'))
        before_body = archive.read_text().split("---", 2)[2]
        prepared = self.prepare({
            "items": [{"id": self.item, "set": {"team_note": "Updated team observation"}}],
            "archive": {"metadata": {"team_note": "Updated"}},
        })
        apply_tracking_update(self.root, prepared["transaction_id"])
        saved = json.loads((self.root / ".ios-workflow/progress.json").read_text())
        self.assertEqual("Updated team observation", saved["items"][0]["team_note"])
        self.assertIn('team_note: "Updated"\n', archive.read_text())
        self.assertEqual(before_body, archive.read_text().split("---", 2)[2])

    def test_invalid_active_recovery_fields_cannot_be_saved(self):
        invalid_fields = [
            ("next_action", None), ("title", 42), ("evidence_key", []),
            ("branch", None), ("observed_head", False), ("updated_at", {}),
            ("current_step", None), ("current_step", "x" * 257),
            ("scope_version", 0), ("scope_version", True), ("scope_version", "2"),
            ("blockers", False), ("blockers", [""]), ("blockers", ["valid", None]),
        ]
        for field, value in invalid_fields:
            with self.subTest(field=field, value=value), self.assertRaisesRegex(TrackingUpdateError, field):
                self.prepare({"active_requirement": {field: value}})
        self.assertEqual(self.fixture.original, self.fixture.targets())
        self.assertFalse((self.root / ".ios-workflow/transactions").exists())
        self.assertEqual([], load_resume_context(self.root, self.req)["errors"])

    def test_valid_long_or_empty_recovery_strings_follow_resume_contract(self):
        prepared = self.prepare({"active_requirement": {
            "next_action": "说明" * 1000, "branch": "", "current_step": "",
            "scope_version": 2, "blockers": [],
        }})
        apply_tracking_update(self.root, prepared["transaction_id"])
        context = load_resume_context(self.root, self.req)
        self.assertEqual([], context["errors"])
        self.assertTrue(context["truncated"])
        saved = json.loads((self.root / ".ios-workflow/index.jsonc").read_text())
        self.assertEqual("说明" * 1000, saved["active_requirement"]["next_action"])

    def test_invalid_existing_summary_requires_explicit_reconciliation(self):
        index = copy.deepcopy(self.fixture.index)
        index["active_requirement"]["next_action"] = None
        self.fixture.install_old_document(".ios-workflow/index.jsonc", index)
        before = self.fixture.targets()
        with self.assertRaisesRegex(TrackingUpdateError, "先恢复或协调现有摘要"):
            read_tracking_snapshot(self.root, self.req)
        with self.assertRaisesRegex(TrackingUpdateError, "先恢复或协调现有摘要"):
            prepare_tracking_patch(self.root, self.req, {"archive": {"append": "New notes"}},
                                   self.fixture.expected)
        self.assertEqual(before, self.fixture.targets())

    def test_omitted_evidence_is_preserved_and_generation_configuration_is_not_read(self):
        generation = self.root / ".ios-workflow/generation/project.jsonc"
        generation.parent.mkdir()
        generation.write_text("invalid historical input")
        result = self.prepare({"archive": {"append": "阶段记录"}})
        apply_tracking_update(self.root, result["transaction_id"])
        self.assertEqual(self.fixture.original[".ios-workflow/progress.json"],
                         (self.root / ".ios-workflow/progress.json").read_text())
        self.assertEqual("invalid historical input", generation.read_text())

    def test_partial_apply_remains_recoverable(self):
        result = self.prepare({"active_requirement": {"next_action": "检查恢复"},
                               "archive": {"append": "新阶段记录"}})
        self.fixture.interrupt(result["transaction_id"])
        restored = recover_tracking_update(self.root, result["transaction_id"])
        self.assertEqual("complete", restored["state"])
        self.assertIn("新阶段记录", (self.root / self.fixture.archive).read_text())

    def test_symlink_cannot_redirect_archive_writes(self):
        archive = self.root / self.fixture.archive
        outside = self.root.parent / "outside.md"
        outside.write_bytes(archive.read_bytes())
        archive.unlink()
        archive.symlink_to(outside)
        before = outside.read_bytes()
        with self.assertRaises((TrackingUpdateError, ValueError)):
            self.prepare({"archive": {"append": "must fail"}})
        self.assertEqual(before, outside.read_bytes())


if __name__ == "__main__":
    unittest.main()
