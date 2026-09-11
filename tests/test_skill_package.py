"""Validate the published Skill structure and portability, not model triggering."""

import importlib.util
import json
import posixpath
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILL = ".agents/skills/ios-workflow"
MODULES = ("project_generation", "progress_validation", "evidence_tools", "resume_context", "change_scope", "tracking_state", "tracking_update", "requirement_gate", "workflow_client", "tracking_patch")
TRACKING_MODULES = ("tracking-start", "tracking-resume", "tracking-evidence", "tracking-sync")


def markdown_targets(markdown):
    """Read the package's inline/reference links, excluding fenced and inline code."""
    lines = []
    fence = None
    for line in markdown.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            value = marker.group(1)
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append(re.sub(r"(`+).*?\1", "", line))
    prose = "\n".join(lines)
    destination = r"(?:<([^>\n]+)>|([^\s)]+))"
    inline = re.compile(r"!?\[[^\]\n]*\]\(\s*" + destination + r"(?:\s+['\"][^\n]*?['\"])?\s*\)")
    definitions = re.compile(r"^\s{0,3}\[[^\]\n]+\]:\s*" + destination, re.MULTILINE)
    return [match.group(1) or match.group(2)
            for pattern in (inline, definitions) for match in pattern.finditer(prose)]


def local_link_errors(document, contents):
    errors = []
    for destination in markdown_targets(contents[document].decode("utf-8")):
        url = urlsplit(destination)
        if url.scheme in {"http", "https", "mailto", "tel", "codex", "app", "data"} or (not url.scheme and url.netloc):
            continue
        path = unquote(url.path)
        if url.scheme or path.startswith("/") or "\\" in path:
            errors.append(f"{document}: local link is not package-relative: {destination}")
            continue
        target = posixpath.normpath(posixpath.join(posixpath.dirname(document), path)) if path else document
        if target == ".." or target.startswith("../"):
            errors.append(f"{document}: local link escapes package: {destination}")
        elif target not in contents and not any(name.startswith(target.rstrip("/") + "/") for name in contents):
            errors.append(f"{document}: missing local link: {destination}")
    return errors


class SkillPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.root = Path(temporary.name)
        spec = importlib.util.spec_from_file_location("skill_package_builder", ROOT / "scripts/build_distribution.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        cls.archive, _ = builder.build_distribution("99.0.0", cls.root / "distribution")
        with zipfile.ZipFile(cls.archive) as archive:
            cls.contents = {name: archive.read(name) for name in archive.namelist()}

    def test_exactly_one_discoverable_skill_with_valid_frontmatter_is_packaged(self):
        discovered = sorted(path.relative_to(ROOT).as_posix()
                            for path in (ROOT / ".agents/skills").rglob("SKILL.md"))
        packaged = sorted(name for name in self.contents if PurePosixPath(name).name == "SKILL.md")
        self.assertEqual([f"{SKILL}/SKILL.md"], discovered)
        self.assertEqual(discovered, packaged)
        text = self.contents[packaged[0]].decode("utf-8")
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
        self.assertIsNotNone(match, "Skill entrypoint must begin with YAML frontmatter")
        fields = {}
        for line in match.group(1).splitlines():
            key, separator, value = line.partition(":")
            self.assertTrue(separator, f"Expected a scalar frontmatter field: {line}")
            self.assertNotIn(key, fields, f"Duplicate frontmatter field: {key}")
            fields[key] = json.loads(value.strip()) if value.strip().startswith('"') else value.strip()
        self.assertEqual("ios-workflow", fields.get("name"))
        self.assertIsInstance(fields.get("description"), str)
        self.assertTrue(fields["description"].strip())
        self.assertIn("iOS", fields["description"])

    def test_agent_interface_uses_quoted_strings_and_the_matching_skill_prompt(self):
        lines = self.contents[f"{SKILL}/agents/openai.yaml"].decode("utf-8").splitlines()
        self.assertEqual("interface:", lines[0])
        fields = {}
        for line in lines[1:]:
            if not line.strip():
                continue
            match = re.fullmatch(r'  ([a-z_]+): ("(?:[^"\\]|\\.)*")', line)
            self.assertIsNotNone(match, f"Metadata must use fixed quoted scalar strings: {line}")
            key = match.group(1)
            self.assertNotIn(key, fields)
            fields[key] = json.loads(match.group(2))
        self.assertEqual({"display_name", "short_description", "default_prompt"}, set(fields))
        self.assertEqual("iOS Workflow", fields["display_name"])
        self.assertTrue(25 <= len(fields["short_description"]) <= 64)
        self.assertRegex(fields["default_prompt"], r"\$ios-workflow(?:\s|[。，！]|$)")

    def test_packaged_entrypoints_and_reference_markdown_have_resolvable_local_links(self):
        documents = sorted(name for name in self.contents
                           if PurePosixPath(name).name == "SKILL.md"
                           or (name.startswith(f"{SKILL}/references/") and name.endswith(".md")))
        self.assertGreater(len(documents), 1)
        self.assertGreater(sum(len(markdown_targets(self.contents[name].decode("utf-8"))) for name in documents), 10)
        errors = [error for document in documents for error in local_link_errors(document, self.contents)]
        self.assertEqual([], errors, "\n".join(errors))

    def test_link_check_handles_anchors_directories_examples_and_missing_repository_files(self):
        document = f"{SKILL}/references/standards/example.md"
        markdown = """[valid](../../scripts/helper.py#function)
[template](../../assets/templates/)
[external](https://example.com/missing.md)
[self](#section)
[reference][guide]
[guide]: <guide.md#section>
```markdown
[placeholder](<项目根目录>/project.md)
```
`[inline example](missing.md)`
"""
        contents = {document: markdown.encode(), f"{SKILL}/scripts/helper.py": b"",
                    f"{SKILL}/assets/templates/example.md": b"", f"{SKILL}/references/standards/guide.md": b""}
        self.assertEqual([], local_link_errors(document, contents))
        contents[document] += b"\n[repository-only](../../../../../README.md)\n[escape](../../../../../../outside.md)"
        errors = local_link_errors(document, contents)
        self.assertEqual(2, len(errors))
        self.assertIn("missing local link", errors[0])
        self.assertIn("escapes package", errors[1])

    def test_packaged_helpers_and_tracking_modules_are_portable_without_repository_or_site_packages(self):
        for module in MODULES:
            self.assertIn(f"{SKILL}/scripts/{module}.py", self.contents)
        for module in TRACKING_MODULES:
            self.assertIn(f"{SKILL}/references/standards/{module}.md", self.contents)
        self.assertIn(f"{SKILL}/assets/templates/tracking/progress.json", self.contents)
        self.assertFalse(any("tests" in PurePosixPath(name).parts or "__pycache__" in PurePosixPath(name).parts
                             for name in self.contents))
        extracted = self.root / "isolated-install"
        with zipfile.ZipFile(self.archive) as archive:
            archive.extractall(extracted)
        scripts = extracted / SKILL / "scripts"
        code = (
            "import importlib, json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "modules = {name: importlib.import_module(name).__file__ for name in sys.argv[2:]}\n"
            "print(json.dumps(modules))\n"
        )
        result = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(scripts), *MODULES],
                                cwd=extracted, text=True, capture_output=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        imported = json.loads(result.stdout)
        self.assertEqual(set(MODULES), set(imported))
        for module, path in imported.items():
            self.assertEqual((scripts / f"{module}.py").resolve(), Path(path).resolve())


if __name__ == "__main__":
    unittest.main()
