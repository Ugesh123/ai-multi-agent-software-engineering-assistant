"""Enumerations shared across the domain, agent, and API layers."""

from __future__ import annotations

from enum import Enum


class AgentRole(str, Enum):
    PLANNER = "planner"
    ARCHITECT = "architect"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DOCUMENTATION = "documentation"


class RunStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    DESIGNING = "designing"
    CODING = "coding"
    REVIEWING = "reviewing"
    TESTING = "testing"
    DOCUMENTING = "documenting"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewVerdict(str, Enum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


class TestVerdict(str, Enum):
    PASSED = "passed"
    FAILED = "failed"


class FileChangeType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
