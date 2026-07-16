"""Bidirectional mappers between ORM rows and domain dataclasses.

Keeping these conversions in one place means the domain layer never has
to import SQLAlchemy, and the ORM layer never has to know about
dataclasses -- both sides stay decoupled per Clean Architecture.
"""

from __future__ import annotations

from dataclasses import asdict

from app.db.models import AgentRunORM, ProjectORM
from app.domain.enums import AgentRole, RunStatus
from app.domain.models import (
    AgentMessage,
    AgentRun,
    ArchitectureDecision,
    GeneratedFile,
    Project,
    ReviewResult,
    TestReport,
)


def project_to_domain(row: ProjectORM) -> Project:
    return Project(
        id=row.id,
        name=row.name,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def project_to_orm(entity: Project) -> ProjectORM:
    return ProjectORM(
        id=entity.id,
        name=entity.name,
        description=entity.description,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _messages_to_domain(raw: list[dict]) -> list[AgentMessage]:
    from datetime import datetime

    result = []
    for item in raw:
        result.append(
            AgentMessage(
                id=item["id"],
                role=AgentRole(item["role"]),
                content=item["content"],
                created_at=datetime.fromisoformat(item["created_at"]),
                metadata=item.get("metadata", {}),
            )
        )
    return result


def run_to_domain(row: AgentRunORM) -> AgentRun:
    return AgentRun(
        id=row.id,
        project_id=row.project_id,
        request=row.request,
        status=RunStatus(row.status),
        parent_run_id=row.parent_run_id,
        version=row.version,
        commit_message=row.commit_message,
        model=row.model,
        plan=[_dict_to_plan_item(p) for p in row.plan or []],
        architecture=ArchitectureDecision(**row.architecture) if row.architecture else None,
        files=[GeneratedFile(**f) for f in row.files or []],
        review=_dict_to_review(row.review) if row.review else None,
        test_report=_dict_to_test_report(row.test_report) if row.test_report else None,
        documentation=row.documentation,
        messages=_messages_to_domain(row.messages or []),
        review_iterations=row.review_iterations,
        test_iterations=row.test_iterations,
        error=row.error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def run_to_orm(entity: AgentRun) -> AgentRunORM:
    return AgentRunORM(
        id=entity.id,
        project_id=entity.project_id,
        request=entity.request,
        status=entity.status.value,
        parent_run_id=entity.parent_run_id,
        version=entity.version,
        commit_message=entity.commit_message,
        model=entity.model,
        plan=[asdict(p) for p in entity.plan],
        architecture=asdict(entity.architecture) if entity.architecture else None,
        files=[asdict(f, dict_factory=_enum_safe_dict) for f in entity.files],
        review=asdict(entity.review, dict_factory=_enum_safe_dict) if entity.review else None,
        test_report=(
            asdict(entity.test_report, dict_factory=_enum_safe_dict)
            if entity.test_report
            else None
        ),
        documentation=entity.documentation,
        messages=[_message_to_dict(m) for m in entity.messages],
        review_iterations=entity.review_iterations,
        test_iterations=entity.test_iterations,
        error=entity.error,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _enum_safe_dict(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        result[key] = value.value if hasattr(value, "value") else value
    return result


def _message_to_dict(message: AgentMessage) -> dict:
    return {
        "id": message.id,
        "role": message.role.value,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "metadata": message.metadata,
    }


def _dict_to_plan_item(raw: dict):
    from app.domain.models import PlanItem

    return PlanItem(**raw)


def _dict_to_review(raw: dict) -> ReviewResult:
    from app.domain.enums import ReviewVerdict
    from app.domain.models import ReviewFinding

    return ReviewResult(
        verdict=ReviewVerdict(raw["verdict"]),
        findings=[ReviewFinding(**f) for f in raw.get("findings", [])],
        summary=raw.get("summary", ""),
    )


def _dict_to_test_report(raw: dict) -> TestReport:
    from app.domain.enums import TestVerdict
    from app.domain.models import TestCaseResult

    return TestReport(
        verdict=TestVerdict(raw["verdict"]),
        cases=[TestCaseResult(**c) for c in raw.get("cases", [])],
        summary=raw.get("summary", ""),
    )
