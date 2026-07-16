import { describe, expect, it } from "vitest";
import { currentStageIndex, PIPELINE_STAGES, stageState, statusLabel } from "../pipeline";

describe("currentStageIndex", () => {
  it("returns -1 for pending", () => {
    expect(currentStageIndex("pending")).toBe(-1);
  });

  it("returns the pipeline length for completed", () => {
    expect(currentStageIndex("completed")).toBe(PIPELINE_STAGES.length);
  });

  it("returns the pipeline length for failed", () => {
    expect(currentStageIndex("failed")).toBe(PIPELINE_STAGES.length);
  });

  it("maps each in-progress status to its matching stage index", () => {
    expect(currentStageIndex("planning")).toBe(0);
    expect(currentStageIndex("designing")).toBe(1);
    expect(currentStageIndex("coding")).toBe(2);
    expect(currentStageIndex("reviewing")).toBe(3);
    expect(currentStageIndex("testing")).toBe(4);
    expect(currentStageIndex("documenting")).toBe(5);
  });
});

describe("stageState", () => {
  it("marks earlier stages as done once the run has progressed past them", () => {
    expect(stageState(0, "coding")).toBe("done"); // planner already finished
    expect(stageState(1, "coding")).toBe("done"); // architect already finished
  });

  it("marks the current stage as active", () => {
    expect(stageState(2, "coding")).toBe("active");
  });

  it("marks later stages as pending", () => {
    expect(stageState(4, "coding")).toBe("pending");
  });

  it("marks all stages done once the run completed", () => {
    for (let i = 0; i < PIPELINE_STAGES.length; i++) {
      expect(stageState(i, "completed")).toBe("done");
    }
  });

  it("marks every stage as failed on a failed run (no partial-progress data available)", () => {
    for (let i = 0; i < PIPELINE_STAGES.length; i++) {
      expect(stageState(i, "failed")).toBe("failed");
    }
  });

  it("marks every stage pending while the run hasn't started", () => {
    for (let i = 0; i < PIPELINE_STAGES.length; i++) {
      expect(stageState(i, "pending")).toBe("pending");
    }
  });
});

describe("statusLabel", () => {
  it("returns a human-readable label for every status", () => {
    expect(statusLabel("pending")).toBe("Queued");
    expect(statusLabel("completed")).toBe("Completed");
    expect(statusLabel("failed")).toBe("Failed");
    expect(statusLabel("coding")).toBe("Writing code");
  });
});
