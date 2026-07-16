"""Assembles the six agents and compiles the LangGraph workflow from
application settings and an `LLMProvider`. This is the single place that
knows how to wire the whole graph together."""

from __future__ import annotations

from app.agents.architect import ArchitectAgent
from app.agents.coder import CoderAgent
from app.agents.documentation import DocumentationAgent
from app.agents.planner import PlannerAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.tester import TesterAgent
from app.core.config import Settings
from app.graph.workflow import build_workflow_graph
from app.llm.base import LLMProvider
from app.services.sandbox_executor import SandboxExecutor


def build_compiled_graph(settings: Settings, llm: LLMProvider):
    sandbox = SandboxExecutor(settings.workspace_root)

    planner = PlannerAgent(llm)
    architect = ArchitectAgent(llm)
    coder = CoderAgent(llm)
    reviewer = ReviewerAgent(llm)
    tester = TesterAgent(llm, sandbox)
    documentation = DocumentationAgent(llm)

    return build_workflow_graph(planner, architect, coder, reviewer, tester, documentation)
