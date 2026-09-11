"""Exercise installed client processes and real files, not model adherence.

The portable resource check below is deliberately narrower than App acceptance:
it executes Python against an App resource and never claims an iOS build or run.
"""

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/ios-workflow"
INSTALLED = Path(".agents/skills/ios-workflow")
REQ = "REQ-EXECUTION-001"
ARCHIVE = f".ios-workflow/requirements/{REQ}.md"
SOURCE = ".ios-workflow/sources/requirements.md"
LEDGERS = (".ios-workflow/index.jsonc", ".ios-workflow/progress.json",
           ".ios-workflow/history.jsonc", ARCHIVE)


def serialize(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


class WorkflowExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ios-workflow-execution-")
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)
        self.project = self.workspace / "device-one/App"
        shutil.copytree(SKILL, self.project / INSTALLED,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.installed_before = self.skill_hashes()
        self.card = {"goal": "Verify a project-local resource contract",
                     "scope": ["Two sample product records"],
                     "acceptance": ["App/catalog.json contains exactly two product records"],
                     "exclusions": ["App runtime, UI, build, signing and publishing"],
                     "assumptions": ["Isolated deterministic integration fixture"]}
        self.write(SOURCE, "# Resource contract\n" + self.card["acceptance"][0] + "\n")
        self.serial = 0

    def write(self, relative, content):
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return relative

    def read(self, relative):
        return json.loads((self.project / relative).read_text(encoding="utf-8"))

    def skill_hashes(self):
        directory = self.project / INSTALLED
        return {path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in directory.rglob("*") if path.is_file()
                and "__pycache__" not in path.parts and path.suffix != ".pyc"}

    def cli(self, command, request=None, *arguments, ok=True):
        argv = [sys.executable, "-B", str(self.project / INSTALLED / "scripts/workflow_client.py"),
                command, "--project-root", str(self.project), *arguments]
        if request is not None:
            self.serial += 1
            path = self.write(f".ios-workflow/client/{self.serial}-{command}.json", serialize(request))
            argv.extend(["--request", path])
        completed = subprocess.run(argv, cwd=self.workspace, capture_output=True, text=True, timeout=20)
        self.assertEqual("", completed.stderr, completed.stderr)
        self.assertEqual(1, len(completed.stdout.splitlines()), completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(ok, result["ok"], result)
        self.assertEqual(0 if ok else 1, completed.returncode, result)
        self.assertEqual(1, result["schema_version"])
        return result["result"]

    def gate(self, phase, *, ok=True):
        return self.cli("gate", {"task_kind": "feature", "phase": phase,
                                 "requirement_id": REQ, "card": self.card}, ok=ok)

    def candidates(self, *, status="ready", item_status="pending", evidence=None,
                   implementation=None, next_action="Implement resource contract"):
        active = {"id": REQ, "project": ".", "status": status, "file": ARCHIVE,
                  "title": self.card["goal"], "current_step": "STEP-001",
                  "next_action": next_action, "blockers": [], "evidence_key": "",
                  "scope_version": 1, "branch": "", "observed_head": "",
                  "updated_at": "2026-09-11T00:00:00Z"}
        index = {"version": 3, "active_requirement": None if status == "done" else active,
                 "last_requirement_id": REQ}
        item = {"id": REQ + "-AC-001", "requirement_id": REQ,
                "criterion": self.card["acceptance"][0], "source": {"path": SOURCE, "section": "Resource contract"},
                "status": item_status, "implementation": implementation or [], "evidence": evidence or []}
        history = {"version": 3, "project": ".", "next_sequence": 2,
                   "execution_order": [{"id": REQ, "sequence": 1, "status": status, "file": ARCHIVE}]}
        archive = (f"---\nid: {REQ}\nproject: .\nstatus: {status}\nsequence: 1\n---\n"
                   f"# Isolated execution fixture\n\nSource: {SOURCE}\n\n"
                   f"Requirement card: {serialize(self.card)}\nNext action: {next_action}\n")
        return dict(zip(LEDGERS, (serialize(index), serialize({"schema_version": 1, "items": [item]}),
                                  serialize(history), archive)))

    def prepare(self, candidates):
        expected = {path: hashlib.sha256((self.project / path).read_bytes()).hexdigest()
                    if (self.project / path).exists() else None for path in LEDGERS}
        prepared = self.cli("prepare", {"requirement_id": REQ, "candidates": candidates,
                                        "expected_hashes": expected})
        return prepared["transaction_id"]

    def persist(self, candidates):
        identifier = self.prepare(candidates)
        self.cli("apply", None, "--transaction-id", identifier)
        self.assertEqual(candidates, {path: (self.project / path).read_text() for path in LEDGERS})

    def relocate(self):
        old = self.project
        self.project = self.workspace / "device-two/different-name"
        shutil.copytree(old, self.project)
        shutil.rmtree(old)
        self.assertFalse(old.exists())

    def test_first_intake_is_persisted_before_real_skeleton_generation(self):
        self.card.update(goal="Generate the explicitly selected iOS skeleton",
                         scope=["SwiftUI, iOS 16, iPhone portrait, English"],
                         acceptance=["project.yml preserves the selected iOS target and UI framework"])
        self.write(SOURCE, "# Resource contract\nSwiftUI; iOS 16; iPhone portrait; English.\n"
                   "The client explicitly selects MVVM, Swift 5, no dependency installation and no Xcode project generation.\n")
        self.gate("start", ok=False)
        self.assertFalse((self.project / "App").exists())
        self.persist(self.candidates())
        self.assertTrue(self.gate("start")["tracking_required"])
        instance = json.loads((ROOT / "docs/configuration-samples/nimblefive/project.json").read_text())
        instance["project_name"] = "IntakeFixture"
        instance["config"].update(dependency_manager="none", generate_xcodeproj=False)
        instance["sources"] = {key: "Isolated client decision; see project sources/requirements.md"
                               for key in instance["sources"]}
        instance["constraints"] = ["Skeleton only; no App functionality or build validation claimed."]
        config = self.write(".ios-workflow/generation/project.jsonc", serialize(instance))
        records_before = {path: (self.project / path).read_bytes() for path in (*LEDGERS, SOURCE, config)}
        code = ("import json,sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
                "from project_generation import materialize_project; "
                "result=materialize_project(Path(sys.argv[2]),Path(sys.argv[3]),allow_project_records=True); "
                "print(json.dumps({'project':result['project'],'file_count':len(result['files'])}))")
        generated = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code,
                                    str(self.project / INSTALLED / "scripts"), str(self.project / config), str(self.project)],
                                   cwd=self.workspace, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, generated.returncode, generated.stderr)
        self.assertIsNone(json.loads(generated.stdout)["project"])
        self.assertGreater(json.loads(generated.stdout)["file_count"], 0)
        definition = (self.project / "project.yml").read_text()
        self.assertIn('iOS: "16.0"', definition)
        self.assertIn('TARGETED_DEVICE_FAMILY: "1"', definition)
        self.assertIn("UIInterfaceOrientationPortrait", definition)
        self.assertTrue((self.project / "App/Features/Home/HomeView.swift").is_file())
        self.assertFalse(list(self.project.glob("*.xcodeproj")))
        self.assertFalse((self.project / "Podfile").exists())
        self.assertEqual(records_before, {path: (self.project / path).read_bytes() for path in records_before})
        self.gate("complete", ok=False)
        self.assertEqual("pending", self.read(LEDGERS[1])["items"][0]["status"])
        self.assertEqual(self.installed_before, self.skill_hashes())

    def test_failed_execution_survives_restart_then_stale_success_blocks_completion(self):
        self.write("project.yml", "name: ExistingApp\n")
        self.write("App/Catalog.swift", 'struct Catalog { static let resource = "catalog" }\n')
        self.write("App/catalog.json", serialize({"products": ["one"]}))
        self.write(".ios-workflow/generation/project.jsonc", "obsolete and intentionally invalid\n")
        checker = self.write("Tests/check_catalog.py", "import json, unittest\nfrom pathlib import Path\n"
                             "class CatalogContract(unittest.TestCase):\n"
                             "    def test_two_product_records(self):\n"
                             "        data = json.loads(Path('App/catalog.json').read_text())\n"
                             "        self.assertEqual(2, len(data['products']))\n"
                             "if __name__ == '__main__': unittest.main(verbosity=2)\n")
        self.persist(self.candidates())
        self.gate("start")
        inputs = [SOURCE, "App/Catalog.swift", "App/catalog.json", "project.yml", checker]
        environment = {"xcode": "Not used: Python resource contract only", "sdk": "Python standard library",
                       "scheme": "CatalogContract", "configuration": "fixture", "destination": platform.platform(),
                       "test_selection": ["CatalogContract.test_two_product_records"], "python": platform.python_version()}

        def run_and_capture(label, expected_code):
            executed = subprocess.run([sys.executable, "-B", checker], cwd=self.project,
                                      capture_output=True, text=True, timeout=15)
            self.assertEqual(expected_code, executed.returncode, executed.stderr)
            self.assertIn("Ran 1 test", executed.stderr)
            report = self.write(f".ios-workflow/evidence/catalog-{label}.txt", executed.stdout + executed.stderr)
            record = f".ios-workflow/evidence-records/catalog-{label}.json"
            captured = self.cli("capture", {"evidence_path": report, "input_paths": inputs,
                                             "environment": environment, "result": "passed" if expected_code == 0 else "failed"},
                                "--output", record)
            self.assertEqual("passed" if expected_code == 0 else "failed", captured["result"])
            return record, self.read(record)

        failed_path, failed = run_and_capture("failed", 1)
        self.assertIn("FAILED (failures=1)", (self.project / failed["path"]).read_text())
        candidate = self.candidates(status="in_progress", item_status="implemented", evidence=[failed],
                                    implementation=["App/Catalog.swift", "App/catalog.json"], next_action="Fix product count and rerun")
        self.persist(candidate)
        self.gate("checkpoint")
        self.gate("complete", ok=False)
        # End the preparing process, move all project files, remove the original
        # path, and recover with the installed client in another fresh process.
        transaction = self.prepare(candidate)
        self.relocate()
        self.cli("recover", None, "--transaction-id", transaction)
        resumed = self.cli("resume", None, "--requirement-id", REQ)
        self.assertEqual("implemented", resumed["items"][0]["recorded_status"])
        self.assertEqual("Fix product count and rerun", resumed["next_action"])
        self.assertEqual("failed", self.read(LEDGERS[1])["items"][0]["evidence"][0]["result"])
        self.assertEqual(failed, self.read(failed_path))
        self.gate("checkpoint")

        self.write("App/catalog.json", serialize({"products": ["one", "two"]}))
        passed_path, passed = run_and_capture("passed", 0)
        compare = {"record_path": passed_path, "current_environment": environment, "current_input_paths": inputs}
        self.assertEqual("matched", self.cli("compare", compare)["status"])
        self.persist(self.candidates(status="done", item_status="verified", evidence=[passed],
                                     implementation=["App/Catalog.swift", "App/catalog.json"], next_action="Resource contract verified only"))
        self.gate("complete")
        before = {path: (self.project / path).read_bytes() for path in LEDGERS}
        self.write("App/catalog.json", serialize({"products": []}))
        self.assertEqual("stale", self.cli("compare", compare, ok=False)["status"])
        self.gate("complete", ok=False)
        self.assertEqual(before, {path: (self.project / path).read_bytes() for path in LEDGERS})
        self.assertEqual("obsolete and intentionally invalid\n", (self.project / ".ios-workflow/generation/project.jsonc").read_text())
        self.assertEqual(self.installed_before, self.skill_hashes())


if __name__ == "__main__":
    unittest.main()
