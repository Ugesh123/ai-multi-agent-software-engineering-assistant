from __future__ import annotations

from app.domain.enums import FileChangeType
from app.domain.models import GeneratedFile
from app.services.diff_service import compute_diff, generate_commit_message


def _file(path: str, content: str) -> GeneratedFile:
    return GeneratedFile(path=path, content=content, change_type=FileChangeType.CREATE)


def test_diff_detects_added_files():
    diff = compute_diff([], [_file("a.py", "x = 1")])
    assert diff.added == ["a.py"]
    assert diff.deleted == []
    assert diff.modified == []


def test_diff_detects_deleted_files():
    diff = compute_diff([_file("a.py", "x = 1")], [])
    assert diff.deleted == ["a.py"]
    assert diff.added == []


def test_diff_detects_modified_files_with_unified_diff():
    old = [_file("a.py", "x = 1\n")]
    new = [_file("a.py", "x = 2\n")]
    diff = compute_diff(old, new)
    assert len(diff.modified) == 1
    assert diff.modified[0].path == "a.py"
    assert "-x = 1" in diff.modified[0].unified_diff
    assert "+x = 2" in diff.modified[0].unified_diff
    assert diff.modified[0].added_lines == 1
    assert diff.modified[0].removed_lines == 1


def test_diff_treats_identical_content_as_unchanged():
    old = [_file("a.py", "same")]
    new = [_file("a.py", "same")]
    diff = compute_diff(old, new)
    assert diff.modified == []
    assert diff.unchanged == ["a.py"]


def test_diff_handles_mixed_changes():
    old = [_file("keep.py", "same"), _file("change.py", "old"), _file("gone.py", "bye")]
    new = [_file("keep.py", "same"), _file("change.py", "new"), _file("fresh.py", "hi")]
    diff = compute_diff(old, new)
    assert diff.added == ["fresh.py"]
    assert diff.deleted == ["gone.py"]
    assert [m.path for m in diff.modified] == ["change.py"]
    assert diff.unchanged == ["keep.py"]
    assert diff.total_changed_files == 3


def test_diff_has_changes_false_for_empty_diff():
    diff = compute_diff([], [])
    assert diff.has_changes is False


def test_commit_message_summarizes_diff_stats():
    old = [_file("a.py", "1")]
    new = [_file("a.py", "2"), _file("b.py", "new")]
    diff = compute_diff(old, new)
    message = generate_commit_message("Add a helper function", diff)
    assert message.startswith("Add a helper function")
    assert "+1 added" in message
    assert "~1 modified" in message


def test_commit_message_truncates_long_requests():
    long_request = "x" * 200
    diff = compute_diff([], [_file("a.py", "1")])
    message = generate_commit_message(long_request, diff)
    assert len(message.split(" (")[0]) <= 72


def test_commit_message_notes_no_changes():
    diff = compute_diff([], [])
    message = generate_commit_message("Do nothing", diff)
    assert "no file changes" in message
