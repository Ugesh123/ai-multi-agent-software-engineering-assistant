import clsx from "clsx";
import { PIPELINE_STAGES, stageState } from "../../lib/pipeline";
import type { RunStatus } from "../../api/types";

interface PipelineRailProps {
  status: RunStatus;
  reviewIterations: number;
  testIterations: number;
}

export function PipelineRail({ status, reviewIterations, testIterations }: PipelineRailProps) {
  return (
    <div className="flex items-center gap-0 overflow-x-auto py-1">
      {PIPELINE_STAGES.map((stage, index) => {
        const state = stageState(index, status);
        const isLast = index === PIPELINE_STAGES.length - 1;
        const retries =
          stage.key === "coder" && (reviewIterations > 0 || testIterations > 0)
            ? Math.max(reviewIterations, testIterations)
            : 0;

        return (
          <div key={stage.key} className="flex items-center">
            <div className="flex flex-col items-center gap-1.5 px-3">
              <div
                className={clsx(
                  "relative flex h-8 w-8 items-center justify-center rounded-full border-2 font-mono text-[11px] font-semibold transition-colors duration-300",
                  state === "pending" && "border-hairline-strong text-text-faint bg-surface",
                  state === "active" && "shadow-[0_0_0_4px_rgba(255,255,255,0.04)]",
                  state === "done" && "border-signal-teal bg-signal-teal/10 text-signal-teal",
                  state === "failed" && "border-signal-red bg-signal-red/10 text-signal-red",
                )}
                style={
                  state === "active"
                    ? { borderColor: stage.color, color: stage.color, background: `${stage.color}1A` }
                    : undefined
                }
              >
                {state === "active" && (
                  <span
                    className="absolute inset-0 animate-ping rounded-full opacity-30"
                    style={{ backgroundColor: stage.color }}
                  />
                )}
                <span className="relative">{index + 1}</span>
                {retries > 0 && (
                  <span className="absolute -right-1.5 -top-1.5 rounded-full bg-signal-amber px-1 text-[9px] font-bold text-ink">
                    ×{retries + 1}
                  </span>
                )}
              </div>
              <span
                className={clsx(
                  "font-mono text-[10px] uppercase tracking-wider",
                  state === "pending" ? "text-text-faint" : "text-text-lo",
                )}
              >
                {stage.label}
              </span>
            </div>
            {!isLast && (
              <div className="relative -mx-1 h-px w-8 flex-shrink-0 bg-hairline-strong sm:w-12">
                <div
                  className={clsx(
                    "absolute inset-0 origin-left bg-signal-teal transition-transform duration-500",
                    state === "done" ? "scale-x-100" : "scale-x-0",
                  )}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
