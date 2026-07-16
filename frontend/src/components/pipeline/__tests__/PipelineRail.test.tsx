import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PipelineRail } from "../PipelineRail";

describe("PipelineRail", () => {
  it("renders all six pipeline stage labels", () => {
    render(<PipelineRail status="pending" reviewIterations={0} testIterations={0} />);
    for (const label of ["Plan", "Design", "Code", "Review", "Test", "Docs"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("shows a retry badge on the Code stage when review iterations occurred", () => {
    render(<PipelineRail status="coding" reviewIterations={1} testIterations={0} />);
    expect(screen.getByText("×2")).toBeInTheDocument();
  });

  it("does not show a retry badge when there have been no retries", () => {
    render(<PipelineRail status="coding" reviewIterations={0} testIterations={0} />);
    expect(screen.queryByText(/×\d/)).not.toBeInTheDocument();
  });
});
