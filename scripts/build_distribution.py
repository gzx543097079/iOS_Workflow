"""为团队分发生成只包含 iOS Skill 和接入说明的可校验压缩包。"""

from __future__ import annotations

import argparse
import hashlib
import re
import zipfile
from pathlib import Path
from typing import Iterable, Tuple


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / ".agents/skills/ios-workflow"
SUPPORT_FILES = {
    ROOT / "distribution/project.example.jsonc": "project.example.jsonc",
    ROOT / "distribution/PROJECT_CONFIGURATION.md": "PROJECT_CONFIGURATION.md",
    ROOT / "distribution/AGENTS.example.md": "AGENTS.ios-workflow.example.md",
    ROOT / "distribution/INSTALL.md": "IOS_WORKFLOW_INSTALL.md",
}
EXCLUDED_NAMES = {".DS_Store", "__pycache__"}


def _skill_files() -> Iterable[Tuple[Path, str]]:
    for path in sorted(SKILL_ROOT.rglob("*")):
        if not path.is_file() or any(part in EXCLUDED_NAMES for part in path.parts) or path.suffix == ".pyc":
            continue
        yield path, path.relative_to(ROOT).as_posix()


def _write_bytes(archive: zipfile.ZipFile, content: bytes, destination: str) -> None:
    info = zipfile.ZipInfo(destination, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, content)


def _write_file(archive: zipfile.ZipFile, source: Path, destination: str) -> None:
    _write_bytes(archive, source.read_bytes(), destination)


def build_distribution(version: str, output: Path) -> Tuple[Path, Path]:
    """生成确定性 ZIP 与 SHA-256 文件，并返回二者路径。"""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("版本号必须使用 major.minor.patch 格式")
    if not (SKILL_ROOT / "SKILL.md").is_file():
        raise FileNotFoundError("未找到 .agents/skills/ios-workflow/SKILL.md")
    for source in SUPPORT_FILES:
        if not source.is_file():
            raise FileNotFoundError(f"缺少分发文件: {source.relative_to(ROOT)}")

    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / f"ios-workflow-{version}.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for source, destination in _skill_files():
            _write_file(archive, source, destination)
        for source, destination in SUPPORT_FILES.items():
            _write_file(archive, source, destination)
        _write_bytes(archive, f"{version}\n".encode(), "IOS_WORKFLOW_VERSION")

    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path = output / f"{archive_path.name}.sha256"
    checksum_path.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")
    return archive_path, checksum_path


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 iOS Workflow 团队分发包")
    parser.add_argument("--version", required=True, help="发布版本，例如 5.0.0")
    parser.add_argument("--output", type=Path, default=ROOT / "dist", help="输出目录")
    arguments = parser.parse_args()
    archive, checksum = build_distribution(arguments.version, arguments.output)
    print(f"分发包: {archive}")
    print(f"校验文件: {checksum}")


if __name__ == "__main__":
    main()
