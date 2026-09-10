import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_distribution import build_distribution


class DistributionTests(unittest.TestCase):
    def test_builds_archive_with_top_level_generation_example(self):
        with tempfile.TemporaryDirectory() as value:
            archive, checksum = build_distribution("5.0.0", Path(value))
            self.assertTrue(archive.is_file())
            self.assertRegex(checksum.read_text(), rf"^[0-9a-f]{{64}}  {archive.name}\n$")
            with zipfile.ZipFile(archive) as package:
                names = set(package.namelist())
                version = package.read("IOS_WORKFLOW_VERSION")
            self.assertIn(".agents/skills/ios-workflow/SKILL.md", names)
            self.assertIn("AGENTS.ios-workflow.example.md", names)
            self.assertIn("IOS_WORKFLOW_INSTALL.md", names)
            self.assertIn("project.example.jsonc", names)
            self.assertIn("PROJECT_CONFIGURATION.md", names)
            self.assertFalse(any(name.startswith(".agents/") and name.endswith("project.example.jsonc") for name in names))
            self.assertEqual(version, b"5.0.0\n")
            self.assertFalse(any(name.startswith(".ios-workflow/") for name in names))
            self.assertFalse(any(".DS_Store" in name or "__pycache__" in name or name.endswith(".pyc") for name in names))

    def test_rejects_non_semantic_version(self):
        with tempfile.TemporaryDirectory() as value:
            with self.assertRaisesRegex(ValueError, "major.minor.patch"):
                build_distribution("latest", Path(value))

    def test_release_workflow_validates_packages_and_publishes(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertRegex(workflow, r"actions/checkout@[0-9a-f]{40}")
        self.assertIn("python3 -m unittest discover -s tests -v", workflow)
        self.assertIn("python3 scripts/build_distribution.py", workflow)
        self.assertIn("gh release create", workflow)


if __name__ == "__main__":
    unittest.main()
