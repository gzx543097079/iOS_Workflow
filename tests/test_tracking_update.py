import copy
import hashlib
import json
import multiprocessing
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/ios-workflow/scripts"))
import tracking_update
from tracking_update import (TrackingUpdateError, prepare_tracking_update, apply_tracking_update,
                             recover_tracking_update, abandon_tracking_update)
from tests import test_progress_validation as progress_fixture


def _hold_lock(project, ready):
    with tracking_update._lock(Path(project)):
        ready.set()
        # Simulate process death; the OS must release the advisory lock.
        os._exit(0)


def _read_fifo(project, relative, result):
    try:
        tracking_update._read(Path(project), relative)
    except TrackingUpdateError:
        result.send(True)
    else:
        result.send(False)
    finally:
        result.close()


class TrackingUpdateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = progress_fixture.ProgressValidationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.project = self.fixture.project
        self.requirement_id = "REQ-001"
        self.archive = ".ios-workflow/requirements/REQ-001.md"
        self.index = {"version": 3, "active_requirement": {
            "id": self.requirement_id, "project": ".", "status": "in_progress", "file": self.archive,
            "title": "Restore", "current_step": "STEP-001", "next_action": "Review", "blockers": [],
            "evidence_key": "fixture", "scope_version": 1, "branch": "main", "observed_head": "fixture", "updated_at": "fixture",
        }}
        self.history = {"version": 3, "project": ".", "next_sequence": 2, "execution_order": [{
            "id": self.requirement_id, "sequence": 1, "status": "in_progress", "file": self.archive,
        }]}
        self.progress = copy.deepcopy(self.fixture.progress)
        self.original = {
            ".ios-workflow/index.jsonc": self.serialize(self.index),
            ".ios-workflow/progress.json": self.serialize(self.progress),
            ".ios-workflow/history.jsonc": self.serialize(self.history),
            self.archive: "---\nid: REQ-001\nproject: .\nstatus: in_progress\nsequence: 1\n---\nOriginal notes\n",
        }
        for path, value in self.original.items():
            target = self.project / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value, encoding="utf-8")
        self.expected = {path: hashlib.sha256(value.encode()).hexdigest() for path, value in self.original.items()}
        self.candidates = dict(self.original)
        for path in (".ios-workflow/index.jsonc", ".ios-workflow/progress.json", ".ios-workflow/history.jsonc"):
            document = json.loads(self.candidates[path])
            document["note"] = "Candidate notes"
            self.candidates[path] = self.serialize(document)
        self.candidates[self.archive] += "Candidate notes\n"

    @staticmethod
    def serialize(value):
        return json.dumps(value, ensure_ascii=False, indent=2) + "\n"

    def targets(self):
        return {path: (self.project / path).read_text(encoding="utf-8") for path in self.original}

    def prepare(self, **kwargs):
        arguments = dict(project_root=self.project, requirement_id=self.requirement_id,
                         candidates=self.candidates, expected_hashes=self.expected)
        arguments.update(kwargs)
        return prepare_tracking_update(**arguments)

    def install_old_document(self, path, document):
        text = self.serialize(document)
        (self.project / path).write_text(text, encoding="utf-8")
        self.original[path] = text
        self.expected[path] = hashlib.sha256(text.encode()).hexdigest()
        self.candidates[path] = text

    def interrupt(self, transaction_id):
        original_write = tracking_update._write
        replacements = []

        def fail_second(*args, **kwargs):
            if kwargs.get("replace"):
                replacements.append(args[1])
                if len(replacements) == 2:
                    raise OSError("simulated interrupted multi-file write")
            return original_write(*args, **kwargs)

        with patch.object(tracking_update, "_write", side_effect=fail_second), self.assertRaises(OSError):
            apply_tracking_update(self.project, transaction_id)
        self.assertEqual(2, len(replacements))

    def test_success_validates_before_targets_change_and_writes_exact_candidate(self):
        before = copy.deepcopy(self.candidates)
        transaction_id = self.prepare()
        self.assertEqual(self.original, self.targets())
        result = apply_tracking_update(self.project, transaction_id)
        self.assertEqual("complete", result["state"])
        self.assertTrue(result["metadata_only"])
        self.assertEqual(self.candidates, self.targets())
        self.assertEqual(before, self.candidates)
        self.assertEqual("in_progress", json.loads(self.targets()[".ios-workflow/index.jsonc"])["active_requirement"]["status"])

    def test_missing_initial_records_can_be_created_with_explicit_none_hashes(self):
        for path in self.original:
            (self.project / path).unlink()
        transaction_id = self.prepare(expected_hashes={path: None for path in self.original})
        apply_tracking_update(self.project, transaction_id)
        self.assertEqual(self.candidates, self.targets())

    def test_invalid_linkage_candidate_never_changes_existing_records(self):
        index = copy.deepcopy(self.index)
        index["active_requirement"]["status"] = "done"
        self.candidates[".ios-workflow/index.jsonc"] = self.serialize(index)
        with self.assertRaises(TrackingUpdateError):
            self.prepare()
        self.assertEqual(self.original, self.targets())
        self.assertEqual([], list((self.project / tracking_update.TRANSACTIONS).glob("*/journal.json")))

    def test_failed_evidence_cannot_be_saved_as_verified(self):
        progress = copy.deepcopy(self.progress)
        progress["items"][0]["evidence"][0]["result"] = "failed"
        self.candidates[".ios-workflow/progress.json"] = self.serialize(progress)
        with self.assertRaises(TrackingUpdateError):
            self.prepare()
        self.assertEqual(self.original, self.targets())

    def test_phase_checkpoint_preserves_failed_result_and_implemented_state(self):
        progress = copy.deepcopy(self.progress)
        progress["items"][0]["status"] = "implemented"
        progress["items"][0]["evidence"][0]["result"] = "failed"
        self.candidates[".ios-workflow/progress.json"] = self.serialize(progress)
        apply_tracking_update(self.project, self.prepare())
        saved = json.loads(self.targets()[".ios-workflow/progress.json"])["items"][0]
        self.assertEqual("implemented", saved["status"])
        self.assertEqual("failed", saved["evidence"][0]["result"])

    def test_stale_expected_hash_including_unrelated_ledger_edit_is_rejected(self):
        progress = copy.deepcopy(self.progress)
        progress["unrelated_change"] = "Keep another device's edit"
        (self.project / ".ios-workflow/progress.json").write_text(self.serialize(progress))
        before = self.targets()
        with self.assertRaises(TrackingUpdateError):
            self.prepare()
        self.assertEqual(before, self.targets())

    def test_pending_prepare_cannot_queue_a_second_update_against_same_old_state(self):
        first = self.prepare()
        with self.assertRaises(TrackingUpdateError):
            self.prepare()
        apply_tracking_update(self.project, first)
        with self.assertRaises(TrackingUpdateError):
            self.prepare()
        self.assertEqual(self.candidates, self.targets())

    def test_interrupted_multi_file_update_is_explicitly_recoverable_and_idempotent(self):
        transaction_id = self.prepare()
        self.interrupt(transaction_id)
        partial = self.targets()
        self.assertEqual(1, sum(partial[path] == self.candidates[path] for path in partial))
        self.assertTrue((self.project / tracking_update.TRANSACTIONS / transaction_id / "journal.json").is_file())
        self.assertFalse((self.project / tracking_update.TRANSACTIONS / transaction_id / "complete").exists())
        self.assertEqual("complete", recover_tracking_update(self.project, transaction_id)["state"])
        self.assertEqual(self.candidates, self.targets())
        before = {path: (self.project / path).stat().st_mtime_ns for path in self.original}
        self.assertEqual("complete", recover_tracking_update(self.project, transaction_id)["state"])
        self.assertEqual(before, {path: (self.project / path).stat().st_mtime_ns for path in self.original})

    def test_recovery_preflights_every_file_before_overwriting_any_remaining_file(self):
        transaction_id = self.prepare()
        self.interrupt(transaction_id)
        target = self.project / self.archive
        target.write_text(self.original[self.archive] + "External edit\n")
        before = self.targets()
        with self.assertRaises(TrackingUpdateError):
            recover_tracking_update(self.project, transaction_id)
        self.assertEqual(before, self.targets())

    def test_edit_of_already_applied_file_also_stops_recovery(self):
        transaction_id = self.prepare()
        self.interrupt(transaction_id)
        first_path = sorted(self.original)[0]
        (self.project / first_path).write_text(self.candidates[first_path] + "\nExternal edit\n")
        before = self.targets()
        with self.assertRaises(TrackingUpdateError):
            recover_tracking_update(self.project, transaction_id)
        self.assertEqual(before, self.targets())

    def test_completed_transaction_does_not_reapply_after_user_reverts_file_to_old_bytes(self):
        transaction_id = self.prepare()
        apply_tracking_update(self.project, transaction_id)
        (self.project / self.archive).write_text(self.original[self.archive])
        before = self.targets()
        with self.assertRaises(TrackingUpdateError):
            recover_tracking_update(self.project, transaction_id)
        self.assertEqual(before, self.targets())

    def test_changed_validation_input_or_staged_candidate_blocks_application(self):
        transaction_id = self.prepare()
        source = self.project / "App/MemoryGrid.swift"
        original = source.read_bytes()
        source.write_bytes(original + b"changed")
        with self.assertRaises(TrackingUpdateError):
            apply_tracking_update(self.project, transaction_id)
        self.assertEqual(self.original, self.targets())
        source.write_bytes(original)
        staged = self.project / tracking_update.TRANSACTIONS / transaction_id / "candidate" / self.archive
        staged.write_text("tampered candidate")
        with self.assertRaises(TrackingUpdateError):
            apply_tracking_update(self.project, transaction_id)
        self.assertEqual(self.original, self.targets())

    def test_symlinked_target_never_changes_the_external_file(self):
        external = Path(self.fixture.temp.name) / "external.md"
        external.write_text(self.original[self.archive])
        target = self.project / self.archive
        target.unlink()
        target.symlink_to(external)
        with self.assertRaises(TrackingUpdateError):
            self.prepare()
        self.assertEqual(self.original[self.archive], external.read_text())
        self.assertTrue(target.is_symlink())

    def test_symlinked_transaction_directory_is_rejected(self):
        external = Path(self.fixture.temp.name) / "outside-transactions"
        external.mkdir()
        (self.project / tracking_update.TRANSACTIONS).symlink_to(external)
        with self.assertRaises((TrackingUpdateError, OSError)):
            self.prepare()
        self.assertEqual([], list(external.iterdir()))
        self.assertEqual(self.original, self.targets())

    def test_unsafe_candidate_paths_and_history_generation_references_are_rejected(self):
        for path in ("../outside.md", "/outside.md", ".ios-workflow/requirements/../outside.md"):
            with self.subTest(path=path):
                candidates = dict(self.candidates)
                candidates[path] = candidates.pop(self.archive)
                with self.assertRaises(TrackingUpdateError):
                    self.prepare(candidates=candidates)
        progress = copy.deepcopy(self.progress)
        progress["items"][0]["source"]["path"] = ".ios-workflow/generation/project.jsonc"
        self.candidates[".ios-workflow/progress.json"] = self.serialize(progress)
        with self.assertRaises(TrackingUpdateError):
            self.prepare()
        self.assertEqual(self.original, self.targets())

    def test_only_selected_dependencies_are_validated_and_copies_are_removed(self):
        progress = copy.deepcopy(self.progress)
        progress["items"].append({"id": "OLD-AC", "requirement_id": "OLD", "evidence": [{"path": "missing-old"}]})
        self.install_old_document(".ios-workflow/progress.json", progress)
        transaction_id = self.prepare()
        transaction = self.project / tracking_update.TRANSACTIONS / transaction_id
        snapshot = transaction / "candidate"
        self.assertFalse((snapshot / "missing-old").exists())
        self.assertFalse((snapshot / "App/MemoryGrid.swift").exists())
        self.assertFalse((snapshot / ".agents").exists())
        self.assertEqual(set(self.candidates), {path.relative_to(snapshot).as_posix()
                                              for path in snapshot.rglob("*") if path.is_file()})
        journal = json.loads((transaction / "journal.json").read_text())
        self.assertIn("App/MemoryGrid.swift", journal["inputs"])
        self.assertNotIn("missing-old", journal["inputs"])

    def test_actual_validated_archive_must_be_the_candidate_archive(self):
        unrelated = ".ios-workflow/requirements/UNRELATED.md"
        candidates = dict(self.candidates)
        candidates.pop(self.archive)
        candidates[unrelated] = "Unrelated unvalidated content\n"
        progress = copy.deepcopy(self.progress)
        progress["items"][0]["implementation"].append(self.archive)
        progress["items"][0]["evidence"][0]["inputs"].append({
            "path": self.archive, "sha256": self.expected[self.archive],
        })
        candidates[".ios-workflow/progress.json"] = self.serialize(progress)
        expected = {path: value for path, value in self.expected.items() if path != self.archive}
        expected[unrelated] = None
        with self.assertRaises(TrackingUpdateError):
            self.prepare(candidates=candidates, expected_hashes=expected)
        self.assertEqual(self.original, self.targets())
        self.assertFalse((self.project / unrelated).exists())

    def test_existing_acceptance_ids_and_other_requirement_items_are_preserved(self):
        path = ".ios-workflow/progress.json"
        progress = copy.deepcopy(self.progress)
        progress["items"].append({"id": "OLD-AC", "requirement_id": "OLD", "note": "Retain"})
        self.install_old_document(path, progress)
        alterations = []
        deleted = copy.deepcopy(progress)
        deleted["items"].pop(0)
        alterations.append(deleted)
        transferred = copy.deepcopy(progress)
        transferred["items"][0]["requirement_id"] = "OTHER"
        alterations.append(transferred)
        edited_other = copy.deepcopy(progress)
        edited_other["items"][1]["note"] = "Discard old work"
        alterations.append(edited_other)
        deleted_other = copy.deepcopy(progress)
        deleted_other["items"].pop(1)
        alterations.append(deleted_other)
        added_other = copy.deepcopy(progress)
        added_other["items"].append({"id": "OTHER-AC", "requirement_id": "OTHER"})
        alterations.append(added_other)
        for alteration in alterations:
            with self.subTest(items=alteration["items"]):
                self.candidates[path] = self.serialize(alteration)
                with self.assertRaises(TrackingUpdateError):
                    self.prepare()
                self.assertEqual(self.original, self.targets())

    def test_existing_execution_rows_and_sequence_allocation_are_preserved(self):
        path = ".ios-workflow/history.jsonc"
        history = copy.deepcopy(self.history)
        history["execution_order"].append({"id": "OLD", "sequence": 2, "status": "done",
                                           "file": ".ios-workflow/requirements/OLD.md"})
        history["next_sequence"] = 3
        self.install_old_document(path, history)
        alterations = []
        edited_other = copy.deepcopy(history)
        edited_other["execution_order"][1]["status"] = "cancelled"
        alterations.append(edited_other)
        deleted = copy.deepcopy(history)
        deleted["execution_order"].pop()
        alterations.append(deleted)
        changed_sequence = copy.deepcopy(history)
        changed_sequence["execution_order"][0]["sequence"] = 4
        changed_sequence["next_sequence"] = 5
        alterations.append(changed_sequence)
        reordered = copy.deepcopy(history)
        reordered["execution_order"].reverse()
        alterations.append(reordered)
        lowered_next = copy.deepcopy(history)
        lowered_next["next_sequence"] = 2
        alterations.append(lowered_next)
        for alteration in alterations:
            with self.subTest(history=alteration):
                self.candidates[path] = self.serialize(alteration)
                with self.assertRaises(TrackingUpdateError):
                    self.prepare()
                self.assertEqual(self.original, self.targets())

    def test_new_execution_record_cannot_reuse_previously_allocated_sequence(self):
        path = ".ios-workflow/history.jsonc"
        old = copy.deepcopy(self.history)
        old["execution_order"] = []
        old["next_sequence"] = 5
        self.install_old_document(path, old)
        proposed = copy.deepcopy(self.history)
        proposed["next_sequence"] = 5
        self.candidates[path] = self.serialize(proposed)
        with self.assertRaises(TrackingUpdateError):
            self.prepare()
        self.assertEqual(self.original, self.targets())

    def test_explicit_abandon_retains_partial_and_external_edits_then_allows_fresh_prepare(self):
        transaction_id = self.prepare()
        self.interrupt(transaction_id)
        (self.project / self.archive).write_text(self.original[self.archive] + "External edit\n")
        before = self.targets()
        with self.assertRaises(TrackingUpdateError):
            recover_tracking_update(self.project, transaction_id)
        result = abandon_tracking_update(self.project, transaction_id)
        self.assertEqual("abandoned", result["state"])
        self.assertTrue(result["requires_reconciliation"])
        self.assertEqual(before, self.targets())
        self.assertTrue((self.project / tracking_update.TRANSACTIONS / transaction_id / "journal.json").is_file())
        self.assertEqual(result, abandon_tracking_update(self.project, transaction_id))
        with self.assertRaises(TrackingUpdateError):
            recover_tracking_update(self.project, transaction_id)
        fresh = dict(self.candidates)
        fresh[self.archive] = before[self.archive] + "Reconciled notes\n"
        hashes = {path: hashlib.sha256(value.encode()).hexdigest() for path, value in before.items()}
        replacement = self.prepare(candidates=fresh, expected_hashes=hashes)
        self.assertNotEqual(transaction_id, replacement)
        apply_tracking_update(self.project, replacement)
        self.assertEqual(fresh, self.targets())

    def test_input_change_during_replacements_cannot_be_reported_complete(self):
        for input_path in ("App/MemoryGrid.swift", ".ios-workflow/evidence/restore-test.txt"):
            with self.subTest(input_path=input_path):
                transaction_id = self.prepare()
                source = self.project / input_path
                original = source.read_bytes()
                original_write = tracking_update._write
                changed = []

                def mutate_after_first_replacement(*args, **kwargs):
                    result = original_write(*args, **kwargs)
                    if kwargs.get("replace") and not changed:
                        source.write_bytes(original + b"changed during update")
                        changed.append(True)
                    return result

                with patch.object(tracking_update, "_write", side_effect=mutate_after_first_replacement):
                    with self.assertRaises(TrackingUpdateError):
                        apply_tracking_update(self.project, transaction_id)
                transaction = self.project / tracking_update.TRANSACTIONS / transaction_id
                self.assertTrue(changed)
                self.assertTrue((transaction / "journal.json").is_file())
                self.assertFalse((transaction / "complete").exists())
                with self.assertRaises(TrackingUpdateError):
                    recover_tracking_update(self.project, transaction_id)
                source.write_bytes(original)
                self.assertEqual("complete", recover_tracking_update(self.project, transaction_id)["state"])
                for path, value in self.original.items():
                    (self.project / path).write_text(value)

    def test_fifo_is_rejected_without_waiting_for_a_writer(self):
        relative = ".ios-workflow/evidence/blocked-pipe"
        os.mkfifo(self.project / relative)
        context = multiprocessing.get_context("spawn")
        received, sent = context.Pipe(duplex=False)
        self.addCleanup(received.close)
        process = context.Process(target=_read_fifo, args=(str(self.project), relative, sent))
        process.start()
        sent.close()
        process.join(5)
        if process.is_alive():
            process.terminate()
            process.join()
            self.fail("FIFO reader blocked before rejecting non-regular input")
        self.assertEqual(0, process.exitcode)
        self.assertTrue(received.poll())
        self.assertTrue(received.recv())

    def test_os_releases_lock_when_lock_owner_process_exits(self):
        context = multiprocessing.get_context("spawn")
        ready = context.Event()
        process = context.Process(target=_hold_lock, args=(str(self.project), ready))
        process.start()
        self.assertTrue(ready.wait(10))
        process.join(10)
        if process.is_alive():
            process.terminate()
            process.join()
            self.fail("lock-owner subprocess failed to exit")
        self.assertEqual(0, process.exitcode)
        self.assertIsInstance(self.prepare(), str)

    def test_another_local_writer_cannot_acquire_held_lock(self):
        with tracking_update._lock(self.project), self.assertRaises(TrackingUpdateError):
            self.prepare()
        self.assertEqual(self.original, self.targets())


if __name__ == "__main__":
    unittest.main()
