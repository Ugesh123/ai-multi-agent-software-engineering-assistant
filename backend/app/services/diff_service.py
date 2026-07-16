"""Computes structured diffs between two versions of a generated project.

Used for the version-history diff viewer (added/modified/deleted files) and
for generating deterministic commit messages -- no LLM call needed, since
this is a pure, verifiable transformation over two known file sets.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from app.domain.models import GeneratedFile


@dataclass(slots=True)
class ModifiedFileDiff:
    path: str
    unified_diff: str
    added_lines: int
    removed_lines: int


@dataclass(slots=True)
class ProjectDiff:
    added: list[str]
    deleted: list[str]
    modified: list[ModifiedFileDiff]
    unchanged: list[str]

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.deleted or self.modified)

    @property
    def total_changed_files(self) -> int:
        return len(self.added) + len(self.deleted) + len(self.modified)


def compute_diff(old_files: list[GeneratedFile], new_files: list[GeneratedFile]) -> ProjectDiff:
    """Compare two complete file sets by path, producing added/deleted/modified
    lists. `old_files` may be empty (diffing against nothing = everything added)."""

    old_by_path = {f.path: f for f in old_files}
    new_by_path = {f.path: f for f in new_files}

    added = sorted(set(new_by_path) - set(old_by_path))
    deleted = sorted(set(old_by_path) - set(new_by_path))
    common = set(old_by_path) & set(new_by_path)

    modified: list[ModifiedFileDiff] = []
    unchanged: list[str] = []

    for path in sorted(common):
        old_content = old_by_path[path].content
        new_content = new_by_path[path].content
        if old_content == new_content:
            unchanged.append(path)
            continue

        diff_lines = list(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
        added_lines = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        removed_lines = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

        modified.append(
            ModifiedFileDiff(
                path=path,
                unified_diff="".join(diff_lines),
                added_lines=added_lines,
                removed_lines=removed_lines,
            )
        )

    return ProjectDiff(added=added, deleted=deleted, modified=modified, unchanged=unchanged)


def generate_commit_message(request: str, diff: ProjectDiff) -> str:
    """Deterministically summarize a diff into a short, git-style commit
    message. No LLM call: the diff stats are exact and don't need to be
    "generated" by a model to be trustworthy."""

    headline = request.strip().splitlines()[0] if request.strip() else "Update project"
    if len(headline) > 72:
        headline = headline[:69].rstrip() + "..."

    if not diff.has_changes:
        return f"{headline} (no file changes)"

    parts = []
    if diff.added:
        parts.append(f"+{len(diff.added)} added")
    if diff.modified:
        parts.append(f"~{len(diff.modified)} modified")
    if diff.deleted:
        parts.append(f"-{len(diff.deleted)} deleted")

    return f"{headline} ({', '.join(parts)})"
