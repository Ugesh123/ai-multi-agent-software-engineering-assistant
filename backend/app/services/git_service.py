"""Real git integration via the `git` CLI (subprocess), one repository per
project under `<workspace_root>/repos/<project_id>`.

Every completed run's file set is a COMPLETE snapshot (see the Coder
agent's merge logic in `app.agents.coder`), so each version can be
mirrored into git as a full working-tree commit rather than an
incremental patch -- git history ends up matching version history
exactly, commit-for-commit.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from app.core.exceptions import WorkflowError
from app.core.logging import get_logger
from app.domain.models import GeneratedFile

logger = get_logger(__name__)

_COMMIT_AUTHOR_NAME = "Multi-Agent Coding Assistant"
_COMMIT_AUTHOR_EMAIL = "agent@localhost"


class GitService:
    def __init__(self, repos_root: Path) -> None:
        self._repos_root = repos_root
        self._repos_root.mkdir(parents=True, exist_ok=True)

    def _repo_dir(self, project_id: str) -> Path:
        return self._repos_root / project_id

    async def _run_git(self, project_id: str, *args: str) -> tuple[int, str, str]:
        repo_dir = self._repo_dir(project_id)
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=str(repo_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        return (
            proc.returncode or 0,
            stdout_bytes.decode(errors="replace"),
            stderr_bytes.decode(errors="replace"),
        )

    async def ensure_repo(self, project_id: str) -> Path:
        repo_dir = self._repo_dir(project_id)
        repo_dir.mkdir(parents=True, exist_ok=True)

        if not (repo_dir / ".git").exists():
            code, _, stderr = await self._run_git(project_id, "init", "-b", "main")
            if code != 0:
                raise WorkflowError(f"git init failed: {stderr.strip()}")
            await self._run_git(project_id, "config", "user.name", _COMMIT_AUTHOR_NAME)
            await self._run_git(project_id, "config", "user.email", _COMMIT_AUTHOR_EMAIL)

        return repo_dir

    async def commit_version(
        self, project_id: str, files: list[GeneratedFile], message: str
    ) -> str | None:
        """Mirror `files` as the complete working tree and commit. Returns
        the new commit hash, or None if nothing changed (no-op commit)."""

        repo_dir = await self.ensure_repo(project_id)

        # Mirror the exact file set: clear tracked content, then rewrite.
        for entry in repo_dir.iterdir():
            if entry.name == ".git":
                continue
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()

        for file in files:
            change_type = file.change_type_value
            if change_type == "delete":
                continue
            target = (repo_dir / file.path).resolve()
            if not str(target).startswith(str(repo_dir.resolve())):
                logger.warning("Skipping file with unsafe path during git commit: %s", file.path)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(file.content, encoding="utf-8")

        await self._run_git(project_id, "add", "-A")
        status_code, status_out, _ = await self._run_git(project_id, "status", "--porcelain")
        if status_code == 0 and not status_out.strip():
            logger.info("git commit skipped for project=%s: no changes", project_id)
            return await self._current_hash(project_id)

        commit_code, _, commit_stderr = await self._run_git(
            project_id, "commit", "-m", message, "--author", f"{_COMMIT_AUTHOR_NAME} <{_COMMIT_AUTHOR_EMAIL}>"
        )
        if commit_code != 0:
            raise WorkflowError(f"git commit failed: {commit_stderr.strip()}")

        return await self._current_hash(project_id)

    async def _current_hash(self, project_id: str) -> str | None:
        code, out, _ = await self._run_git(project_id, "rev-parse", "HEAD")
        return out.strip() if code == 0 else None

    async def get_log(self, project_id: str) -> list[dict]:
        repo_dir = self._repo_dir(project_id)
        if not (repo_dir / ".git").exists():
            return []

        code, out, _ = await self._run_git(
            project_id, "log", "--pretty=format:%H%x1f%an%x1f%ad%x1f%s", "--date=iso-strict"
        )
        if code != 0 or not out.strip():
            return []

        commits = []
        for line in out.strip().split("\n"):
            parts = line.split("\x1f")
            if len(parts) != 4:
                continue
            commit_hash, author, date, subject = parts
            commits.append({"hash": commit_hash, "author": author, "date": date, "message": subject})
        return commits

    async def set_remote(self, project_id: str, remote_url: str) -> None:
        await self.ensure_repo(project_id)
        await self._run_git(project_id, "remote", "remove", "origin")
        code, _, stderr = await self._run_git(project_id, "remote", "add", "origin", remote_url)
        if code != 0:
            raise WorkflowError(f"git remote add failed: {stderr.strip()}")

    async def push(
        self, project_id: str, remote_url: str, token: str | None = None, branch: str = "main"
    ) -> dict:
        """Push to `remote_url`. If `token` is given, it's injected into the
        URL transiently for this push only (never persisted, never logged)."""

        await self.ensure_repo(project_id)

        push_url = remote_url
        if token and remote_url.startswith("https://"):
            push_url = remote_url.replace("https://", f"https://x-access-token:{token}@", 1)

        code, out, stderr = await self._run_git(project_id, "push", push_url, f"HEAD:{branch}")
        if code != 0:
            # Strip any credential-embedded URL from the error before surfacing it.
            safe_stderr = stderr.replace(push_url, remote_url)
            raise WorkflowError(f"git push failed: {safe_stderr.strip()}")

        return {"success": True, "output": out.strip() or stderr.strip()}
