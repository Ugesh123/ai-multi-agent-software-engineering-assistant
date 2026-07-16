import type { RunStatus } from "../api/types";

export interface PipelineStage {
  key: string;
  label: string;
  /** The status value the graph reports while this agent is actively running. */
  activeStatus: RunStatus;
  /** Signal color token (see index.css @theme) used when this stage is active. */
  color: string;
}

// Order mirrors the actual LangGraph node sequence in app/graph/workflow.py.
export const PIPELINE_STAGES: PipelineStage[] = [
  { key: "planner", label: "Plan", activeStatus: "planning", color: "var(--color-signal-blue)" },
  { key: "architect", label: "Design", activeStatus: "designing", color: "var(--color-signal-violet)" },
  { key: "coder", label: "Code", activeStatus: "coding", color: "var(--color-signal-amber)" },
  { key: "reviewer", label: "Review", activeStatus: "reviewing", color: "var(--color-signal-violet)" },
  { key: "tester", label: "Test", activeStatus: "testing", color: "var(--color-signal-teal)" },
  { key: "documentation", label: "Docs", activeStatus: "documenting", color: "var(--color-signal-blue)" },
];

const STATUS_ORDER: RunStatus[] = [
  "pending",
  "planning",
  "designing",
  "coding",
  "reviewing",
  "testing",
  "documenting",
  "completed",
];

/** Index (0-5) of the pipeline stage currently active for a given status,
 * or -1 if pending, or PIPELINE_STAGES.length if completed/failed. */
export function currentStageIndex(status: RunStatus): number {
  if (status === "pending") return -1;
  if (status === "completed" || status === "failed") return PIPELINE_STAGES.length;
  return PIPELINE_STAGES.findIndex((s) => s.activeStatus === status);
}

/** Whether a given stage has already been passed (completed) at least once. */
export function stageState(
  stageIndex: number,
  status: RunStatus,
): "pending" | "active" | "done" | "failed" {
  // A failed run doesn't retain which stage it failed at in this data model
  // (status becomes the terminal "failed" value), so every stage is shown
  // as failed rather than guessing partial progress.
  if (status === "failed") return "failed";

  const current = currentStageIndex(status);
  if (current === PIPELINE_STAGES.length) return "done"; // whole run completed
  if (stageIndex < current) return "done";
  if (stageIndex === current) return "active";
  return "pending";
}

export function statusLabel(status: RunStatus): string {
  const map: Record<RunStatus, string> = {
    pending: "Queued",
    planning: "Planning",
    designing: "Designing architecture",
    coding: "Writing code",
    reviewing: "Reviewing code",
    testing: "Running tests",
    documenting: "Writing docs",
    completed: "Completed",
    failed: "Failed",
  };
  return map[status];
}

const STATUS_ORDER_SET = new Set(STATUS_ORDER);
export function isKnownStatus(status: string): status is RunStatus {
  return STATUS_ORDER_SET.has(status as RunStatus) || status === "failed";
}
