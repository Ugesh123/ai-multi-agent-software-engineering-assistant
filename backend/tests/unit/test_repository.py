from __future__ import annotations

import pytest

from app.core.exceptions import NotFoundError
from app.db.repository import SqlAlchemyAgentRunRepository, SqlAlchemyProjectRepository
from app.domain.enums import AgentRole, ReviewVerdict, RunStatus
from app.domain.models import AgentRun, PlanItem, Project, ReviewFinding, ReviewResult

pytestmark = pytest.mark.asyncio


async def test_create_and_get_project(db_session):
    repo = SqlAlchemyProjectRepository(db_session)
    project = Project(name="Test Project", description="A test project")

    created = await repo.create(project)
    await db_session.commit()

    fetched = await repo.get(created.id)
    assert fetched.id == created.id
    assert fetched.name == "Test Project"


async def test_get_missing_project_raises(db_session):
    repo = SqlAlchemyProjectRepository(db_session)
    with pytest.raises(NotFoundError):
        await repo.get("does-not-exist")


async def test_list_all_projects_ordered(db_session):
    repo = SqlAlchemyProjectRepository(db_session)
    await repo.create(Project(name="First"))
    await repo.create(Project(name="Second"))
    await db_session.commit()

    projects = await repo.list_all()
    assert len(projects) == 2


async def test_agent_run_round_trip_with_nested_data(db_session):
    project_repo = SqlAlchemyProjectRepository(db_session)
    run_repo = SqlAlchemyAgentRunRepository(db_session)

    project = await project_repo.create(Project(name="Round Trip"))
    await db_session.flush()

    run = AgentRun(
        project_id=project.id,
        request="Build a CLI todo app",
        status=RunStatus.PLANNING,
        plan=[PlanItem(title="Set up project skeleton", order=0)],
    )
    run.record(AgentRole.PLANNER, "Created a 3-step plan")

    created = await run_repo.create(run)
    await db_session.commit()

    fetched = await run_repo.get(created.id)
    assert fetched.request == "Build a CLI todo app"
    assert fetched.status == RunStatus.PLANNING
    assert len(fetched.plan) == 1
    assert fetched.plan[0].title == "Set up project skeleton"
    assert len(fetched.messages) == 1
    assert fetched.messages[0].role == AgentRole.PLANNER


async def test_agent_run_update_persists_review(db_session):
    project_repo = SqlAlchemyProjectRepository(db_session)
    run_repo = SqlAlchemyAgentRunRepository(db_session)

    project = await project_repo.create(Project(name="Update Test"))
    await db_session.flush()

    run = AgentRun(project_id=project.id, request="Build something")
    created = await run_repo.create(run)
    await db_session.commit()

    created.status = RunStatus.REVIEWING
    created.review = ReviewResult(
        verdict=ReviewVerdict.CHANGES_REQUESTED,
        findings=[ReviewFinding(file_path="main.py", severity="major", message="Missing tests")],
        summary="Needs test coverage",
    )
    updated = await run_repo.update(created)
    await db_session.commit()

    fetched = await run_repo.get(updated.id)
    assert fetched.status == RunStatus.REVIEWING
    assert fetched.review is not None
    assert fetched.review.verdict == ReviewVerdict.CHANGES_REQUESTED
    assert fetched.review.findings[0].file_path == "main.py"


async def test_get_max_version_returns_zero_for_project_with_no_runs(db_session):
    project_repo = SqlAlchemyProjectRepository(db_session)
    run_repo = SqlAlchemyAgentRunRepository(db_session)

    project = await project_repo.create(Project(name="Empty"))
    await db_session.flush()

    assert await run_repo.get_max_version(project.id) == 0


async def test_get_max_version_returns_highest_version(db_session):
    project_repo = SqlAlchemyProjectRepository(db_session)
    run_repo = SqlAlchemyAgentRunRepository(db_session)

    project = await project_repo.create(Project(name="Versioned"))
    await db_session.flush()

    for v in (1, 3, 2):
        await run_repo.create(AgentRun(project_id=project.id, request="x", version=v))
    await db_session.commit()

    assert await run_repo.get_max_version(project.id) == 3


async def test_get_max_version_isolated_per_project(db_session):
    project_repo = SqlAlchemyProjectRepository(db_session)
    run_repo = SqlAlchemyAgentRunRepository(db_session)

    project_a = await project_repo.create(Project(name="A"))
    project_b = await project_repo.create(Project(name="B"))
    await db_session.flush()

    await run_repo.create(AgentRun(project_id=project_a.id, request="x", version=5))
    await db_session.commit()

    assert await run_repo.get_max_version(project_a.id) == 5
    assert await run_repo.get_max_version(project_b.id) == 0
