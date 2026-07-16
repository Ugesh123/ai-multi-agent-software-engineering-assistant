from __future__ import annotations

import subprocess

import pytest

from app.core.exceptions import WorkflowError
from app.domain.enums import FileChangeType
from app.domain.models import GeneratedFile
from app.services.git_service import GitService

pytestmark = pytest.mark.asyncio


def _files(*pairs: tuple[str, str]) -> list[GeneratedFile]:
    return [GeneratedFile(path=p, content=c, change_type=FileChangeType.CREATE) for p, c in pairs]


async def test_ensure_repo_initializes_git_repo(tmp_path):
    service = GitService(tmp_path / "repos")
    repo_dir = await service.ensure_repo("proj-1")
    assert (repo_dir / ".git").exists()


async def test_ensure_repo_is_idempotent(tmp_path):
    service = GitService(tmp_path / "repos")
    await service.ensure_repo("proj-1")
    # Calling again must not fail or reinitialize destructively.
    repo_dir = await service.ensure_repo("proj-1")
    assert (repo_dir / ".git").exists()


async def test_commit_version_creates_real_commit_with_files(tmp_path):
    service = GitService(tmp_path / "repos")
    commit_hash = await service.commit_version(
        "proj-1", _files(("app/core.py", "print('v1')")), "Initial version"
    )
    assert commit_hash is not None
    assert len(commit_hash) == 40  # full SHA-1

    repo_dir = tmp_path / "repos" / "proj-1"
    assert (repo_dir / "app" / "core.py").read_text() == "print('v1')"


async def test_commit_version_mirrors_full_file_set_across_versions(tmp_path):
    """Each commit should reflect the COMPLETE file set for that version --
    files removed in a later version must disappear from the working tree."""

    service = GitService(tmp_path / "repos")
    await service.commit_version(
        "proj-1", _files(("a.py", "one"), ("b.py", "two")), "v1"
    )
    await service.commit_version("proj-1", _files(("a.py", "one-updated")), "v2 (b.py removed)")

    repo_dir = tmp_path / "repos" / "proj-1"
    assert (repo_dir / "a.py").read_text() == "one-updated"
    assert not (repo_dir / "b.py").exists()


async def test_commit_version_skips_noop_commit(tmp_path):
    service = GitService(tmp_path / "repos")
    files = _files(("a.py", "same content"))

    hash1 = await service.commit_version("proj-1", files, "v1")
    hash2 = await service.commit_version("proj-1", files, "v2 (identical content)")

    # No actual changes -- commit_version should not create an empty commit.
    assert hash1 == hash2


async def test_get_log_returns_commits_in_order(tmp_path):
    service = GitService(tmp_path / "repos")
    await service.commit_version("proj-1", _files(("a.py", "v1")), "First version")
    await service.commit_version("proj-1", _files(("a.py", "v2")), "Second version")

    log = await service.get_log("proj-1")
    assert len(log) == 2
    # git log is newest-first.
    assert log[0]["message"] == "Second version"
    assert log[1]["message"] == "First version"
    assert all(len(entry["hash"]) == 40 for entry in log)


async def test_get_log_returns_empty_for_uninitialized_project(tmp_path):
    service = GitService(tmp_path / "repos")
    log = await service.get_log("never-touched")
    assert log == []


async def test_push_to_local_bare_repo_succeeds(tmp_path):
    """Real end-to-end push test: creates an actual local bare git repo to
    act as the 'remote' (no network required), and verifies the pushed
    commit is genuinely present in that remote afterward."""

    bare_remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare_remote)], check=True, capture_output=True)

    service = GitService(tmp_path / "repos")
    commit_hash = await service.commit_version(
        "proj-1", _files(("app/core.py", "print('hello')")), "Initial commit"
    )

    result = await service.push("proj-1", str(bare_remote))
    assert result["success"] is True

    # Verify for real: the bare remote must now contain that exact commit.
    log_output = subprocess.run(
        ["git", "log", "--pretty=%H", "main"],
        cwd=str(bare_remote),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert commit_hash in log_output.split("\n")


async def test_push_to_nonexistent_remote_raises(tmp_path):
    service = GitService(tmp_path / "repos")
    await service.commit_version("proj-1", _files(("a.py", "x")), "v1")

    with pytest.raises(WorkflowError):
        await service.push("proj-1", str(tmp_path / "does-not-exist.git"))


async def test_set_remote_configures_origin(tmp_path):
    bare_remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(bare_remote)], check=True, capture_output=True)

    service = GitService(tmp_path / "repos")
    await service.set_remote("proj-1", str(bare_remote))

    repo_dir = tmp_path / "repos" / "proj-1"
    result = subprocess.run(
        ["git", "remote", "-v"], cwd=str(repo_dir), check=True, capture_output=True, text=True
    )
    assert str(bare_remote) in result.stdout


async def test_push_error_message_does_not_leak_token(tmp_path):
    service = GitService(tmp_path / "repos")
    await service.commit_version("proj-1", _files(("a.py", "x")), "v1")

    fake_remote = "https://github.com/nonexistent/repo-that-does-not-exist-xyz.git"
    with pytest.raises(WorkflowError) as exc_info:
        await service.push("proj-1", fake_remote, token="super-secret-token")

    assert "super-secret-token" not in str(exc_info.value)
