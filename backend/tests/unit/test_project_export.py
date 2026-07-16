from __future__ import annotations

import io
import zipfile

from app.domain.enums import FileChangeType
from app.domain.models import AgentRun, GeneratedFile
from app.services.project_export_service import build_project_zip


def test_zip_contains_generated_files_and_readme():
    run = AgentRun(
        project_id="p1",
        request="Build a calculator",
        files=[
            GeneratedFile(path="app/core.py", content="def run(): pass", change_type=FileChangeType.CREATE),
            GeneratedFile(path="tests/test_core.py", content="def test_x(): pass", change_type=FileChangeType.CREATE),
        ],
        documentation="# My Project\n\nDetails here.",
    )

    zip_bytes = build_project_zip(run)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = set(archive.namelist())
        assert "app/core.py" in names
        assert "tests/test_core.py" in names
        assert "README.md" in names
        assert archive.read("README.md").decode() == "# My Project\n\nDetails here."


def test_zip_excludes_deleted_files():
    run = AgentRun(
        project_id="p1",
        request="x",
        files=[
            GeneratedFile(path="keep.py", content="ok", change_type=FileChangeType.CREATE),
            GeneratedFile(path="gone.py", content="stale", change_type=FileChangeType.DELETE),
        ],
    )

    zip_bytes = build_project_zip(run)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = set(archive.namelist())
        assert "keep.py" in names
        assert "gone.py" not in names


def test_zip_does_not_duplicate_existing_readme():
    run = AgentRun(
        project_id="p1",
        request="x",
        files=[GeneratedFile(path="README.md", content="custom readme", change_type=FileChangeType.CREATE)],
        documentation="generated readme content",
    )

    zip_bytes = build_project_zip(run)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        assert archive.namelist().count("README.md") == 1
        assert archive.read("README.md").decode() == "custom readme"


def test_zip_rejects_path_traversal_entries():
    run = AgentRun(
        project_id="p1",
        request="x",
        files=[
            GeneratedFile(path="../../etc/passwd", content="malicious", change_type=FileChangeType.CREATE),
            GeneratedFile(path="/etc/shadow", content="malicious", change_type=FileChangeType.CREATE),
            GeneratedFile(path="safe/file.py", content="fine", change_type=FileChangeType.CREATE),
        ],
    )

    zip_bytes = build_project_zip(run)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = archive.namelist()
        assert "safe/file.py" in names
        assert not any(".." in n for n in names)
        assert not any(n.startswith("/") for n in names)


def test_zip_rejects_windows_drive_letter_paths():
    run = AgentRun(
        project_id="p1",
        request="x",
        files=[GeneratedFile(path="C:\\Windows\\System32\\evil.dll", content="x", change_type=FileChangeType.CREATE)],
    )

    zip_bytes = build_project_zip(run)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        assert archive.namelist() == []
