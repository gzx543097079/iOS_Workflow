import json
import subprocess
import sys
import unittest
from pathlib import Path

from tests import test_evidence_tools as evidence_fixtures
from tests import test_tracking_update as tracking_fixtures


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents/skills/ios-workflow/scripts/workflow_client.py"
sys.path.insert(0, str(SCRIPT.parent))
from workflow_client import run_command


class WorkflowClientTests(unittest.TestCase):
    def setUp(self):
        self.fixture = tracking_fixtures.TrackingUpdateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.project
        self.card = {"goal": "Local client fixture", "scope": ["Restore"],
                     "acceptance": ["A restart preserves the saved state"],
                     "exclusions": [], "assumptions": []}

    def request_file(self, value, name="request.jsonc", root=None):
        relative = f".ios-workflow/client/{name}"
        target = (root or self.root) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return relative

    def cli(self, command, *arguments, root=None):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), command, "--project-root", str(root or self.root), *arguments],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual("", completed.stderr)
        self.assertEqual(1, len(completed.stdout.splitlines()))
        result = json.loads(completed.stdout)
        self.assertEqual(1, result["schema_version"])
        self.assertEqual(0 if result["ok"] else 1, completed.returncode)
        return result

    def prepare_request(self):
        return {"requirement_id": self.fixture.requirement_id,
                "candidates": self.fixture.candidates, "expected_hashes": self.fixture.expected}

    def test_gate_and_resume_use_real_records_without_echoing_card_or_archive(self):
        self.card["goal"] = "PRIVATE_FULL_CARD_MARKER"
        request = self.request_file({"task_kind": "feature", "phase": "start", "card": self.card,
                                     "requirement_id": "REQ-001"})
        before = self.fixture.targets()
        result = self.cli("gate", "--request", request)
        self.assertTrue(result["ok"])
        self.assertTrue(result["result"]["tracking_required"])
        self.assertNotIn("PRIVATE_FULL_CARD_MARKER", json.dumps(result))
        resumed = self.cli("resume", "--requirement-id", "REQ-001", "--max-items", "1")
        self.assertTrue(resumed["ok"])
        self.assertEqual("in_progress", resumed["result"]["recorded_status"])
        self.assertNotIn("Original notes", json.dumps(resumed))
        self.assertEqual(before, self.fixture.targets())

    def test_missing_feature_records_or_premature_completion_return_nonzero(self):
        for phase, requirement in (("start", None), ("complete", "REQ-001")):
            with self.subTest(phase=phase):
                path = self.request_file({"task_kind": "feature", "phase": phase,
                                          "card": self.card, "requirement_id": requirement})
                result = self.cli("gate", "--request", path)
                self.assertFalse(result["ok"])
                self.assertGreater(result["error_count"], 0)

    def test_snapshot_and_field_update_run_without_sending_full_records(self):
        snapshot = self.cli("snapshot", "--requirement-id", "REQ-001")
        self.assertTrue(snapshot["ok"], snapshot)
        request = self.request_file({"requirement_id": "REQ-001",
                                     "expected_hashes": snapshot["result"]["expected_hashes"],
                                     "updates": {"active_requirement": {"next_action": "Check updated snapshot"},
                                                 "archive": {"append": "PRIVATE_APPEND_MARKER"}}})
        prepared = self.cli("prepare-update", "--request", request)
        self.assertTrue(prepared["ok"], prepared)
        self.assertNotIn("PRIVATE_APPEND_MARKER", json.dumps(prepared))
        self.assertEqual(2, len(prepared["result"]["changed_files"]))
        self.assertTrue(self.cli("apply", "--transaction-id", prepared["result"]["transaction_id"])["ok"])
        self.assertEqual("Check updated snapshot", self.cli("resume", "--requirement-id", "REQ-001")["result"]["next_action"])
        self.assertFalse(self.cli("prepare-update", "--request", request)["ok"], "old request must not be rebased")

    def test_prepare_then_separate_process_apply_preserves_exact_candidates(self):
        request = self.request_file(self.prepare_request())
        prepared = self.cli("prepare", "--request", request)
        self.assertTrue(prepared["ok"], prepared)
        self.assertEqual("prepared", prepared["result"]["state"])
        self.assertEqual(self.fixture.original, self.fixture.targets())
        self.assertNotIn("Candidate notes", json.dumps(prepared))
        applied = self.cli("apply", "--transaction-id", prepared["result"]["transaction_id"])
        self.assertTrue(applied["ok"], applied)
        self.assertEqual(self.fixture.candidates, self.fixture.targets())
        recovered = self.cli("recover", "--transaction-id", prepared["result"]["transaction_id"])
        self.assertEqual("complete", recovered["result"]["state"])

    def test_conflicting_apply_fails_and_abandon_does_not_overwrite_edit(self):
        prepared = run_command("prepare", self.root, self.prepare_request())
        self.assertTrue(prepared["ok"], prepared)
        identifier = prepared["result"]["transaction_id"]
        archive = self.root / self.fixture.archive
        archive.write_text("External editor contents\n", encoding="utf-8")
        self.assertFalse(self.cli("apply", "--transaction-id", identifier)["ok"])
        self.assertFalse(self.cli("recover", "--transaction-id", identifier)["ok"])
        abandoned = self.cli("abandon", "--transaction-id", identifier)
        self.assertTrue(abandoned["ok"])
        self.assertTrue(abandoned["result"]["requires_reconciliation"])
        self.assertEqual("External editor contents\n", archive.read_text())
        self.assertFalse(self.cli("apply", "--transaction-id", identifier)["ok"])

    def test_request_paths_reject_escape_symlink_and_historical_configuration(self):
        request = self.request_file({"task_kind": "maintenance", "phase": "start", "card": self.card,
                                     "low_risk": True, "single_turn": True, "acceptance_clear": True})
        (self.root / ".ios-workflow/client/link.json").symlink_to(self.root / request)
        generation = self.root / ".ios-workflow/generation/project.jsonc"
        generation.parent.mkdir(parents=True)
        generation.write_text((self.root / request).read_text())
        for relative in ("../outside.json", str(self.root / request),
                         ".ios-workflow/client/link.json", ".ios-workflow/generation/project.jsonc"):
            with self.subTest(path=relative):
                self.assertFalse(self.cli("gate", "--request", relative)["ok"])

    def test_malformed_requests_and_unknown_fields_fail_without_echoing_payload(self):
        request = self.request_file({})
        target = self.root / request
        invalid = ("PRIVATE_REQUEST_CONTENT is not JSON",
                   '{"card": "PRIVATE_REQUEST_CONTENT", "card": {}}',
                   '{"card": NaN}', '[]',
                   '{"PRIVATE_REQUEST_CONTENT": "extra field"}')
        for content in invalid:
            with self.subTest(content=content):
                target.write_text(content)
                response = self.cli("gate", "--request", request)
                self.assertFalse(response["ok"])
                self.assertNotIn("PRIVATE_REQUEST_CONTENT", json.dumps(response))

    def test_invalid_cli_arguments_also_return_json(self):
        self.assertFalse(self.cli("resume", "--max-items", "not-an-integer")["ok"])
        self.assertFalse(self.cli("resume", "--max-items", "0")["ok"])
        self.assertFalse(self.cli("gate")["ok"])
        self.assertFalse(self.cli("unknown")["ok"])

    def test_missing_project_cannot_receive_maintenance_success(self):
        result = run_command("gate", self.root / "does-not-exist", {
            "task_kind": "maintenance", "phase": "start", "card": self.card,
            "low_risk": True, "single_turn": True, "acceptance_clear": True,
        })
        self.assertFalse(result["ok"])

    def test_capture_stores_record_locally_and_compare_detects_changed_input(self):
        fixture = evidence_fixtures.EvidenceToolsTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        request = self.request_file({
            "evidence_path": fixture.evidence, "input_paths": fixture.inputs,
            "environment": fixture.environment, "result": "passed",
        }, root=fixture.project)
        record_path = ".ios-workflow/evidence-records/test-run.json"
        captured = self.cli("capture", "--request", request, "--output", record_path, root=fixture.project)
        self.assertTrue(captured["ok"], captured)
        self.assertEqual(len(fixture.inputs), captured["result"]["input_count"])
        self.assertNotIn("inputs", captured["result"])
        record_file = fixture.project / record_path
        record = json.loads(record_file.read_text())
        self.assertEqual(fixture.record["sha256"], record["sha256"])
        self.assertEqual(fixture.record["inputs"], record["inputs"])
        before = record_file.read_bytes()
        self.assertFalse(self.cli("capture", "--request", request, "--output", record_path, root=fixture.project)["ok"])
        self.assertEqual(before, record_file.read_bytes())
        compare = self.request_file({
            "record_path": record_path, "current_environment": fixture.environment,
            "current_input_paths": fixture.inputs,
        }, name="compare.json", root=fixture.project)
        self.assertTrue(self.cli("compare", "--request", compare, root=fixture.project)["ok"])
        (fixture.project / "App/Game.swift").write_text("changed implementation")
        stale = self.cli("compare", "--request", compare, root=fixture.project)
        self.assertFalse(stale["ok"])
        self.assertEqual("stale", stale["result"]["status"])

    def test_failed_evidence_can_be_recorded_but_not_reused_as_success(self):
        fixture = evidence_fixtures.EvidenceToolsTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        request = {"evidence_path": fixture.evidence, "input_paths": fixture.inputs,
                   "environment": fixture.environment, "result": "failed"}
        record_path = ".ios-workflow/evidence-records/failure.json"
        captured = run_command("capture", fixture.project, request, output=record_path)
        self.assertTrue(captured["ok"])
        self.assertEqual("failed", captured["result"]["result"])
        compared = run_command("compare", fixture.project, {
            "record_path": record_path, "current_environment": fixture.environment,
            "current_input_paths": fixture.inputs,
        })
        self.assertFalse(compared["ok"])
        self.assertEqual("stale", compared["result"]["status"])

    def test_capture_cannot_write_outside_record_directory_or_through_symlink(self):
        fixture = evidence_fixtures.EvidenceToolsTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        request = {"evidence_path": fixture.evidence, "input_paths": fixture.inputs,
                   "environment": fixture.environment, "result": "passed"}
        source = fixture.project / "App/Game.swift"
        before = source.read_bytes()
        for path in ("App/Game.swift", ".ios-workflow/progress.json",
                     ".ios-workflow/evidence-records/../../escaped.json"):
            with self.subTest(path=path):
                self.assertFalse(run_command("capture", fixture.project, request, output=path)["ok"])
        outside = Path(fixture.temp.name) / "outside"
        outside.mkdir()
        (fixture.project / ".ios-workflow/evidence-records").symlink_to(outside)
        self.assertFalse(run_command("capture", fixture.project, request,
                                     output=".ios-workflow/evidence-records/run.json")["ok"])
        self.assertEqual([], list(outside.iterdir()))
        self.assertEqual(before, source.read_bytes())
