import { CheckCircle2, TerminalSquare, XCircle } from "lucide-react";
import clsx from "clsx";
import type { TestReport } from "../../api/types";
import { EmptyState } from "./ReviewPanel";

export function TestsPanel({ report }: { report: TestReport | null }) {
  if (!report) {
    return <EmptyState message="No test results yet. Tests run for real in a sandbox after review." />;
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4">
      <div
        className={clsx(
          "mb-4 flex items-center gap-2 rounded-md border px-3 py-2 text-sm",
          report.verdict === "passed"
            ? "border-signal-teal/30 bg-signal-teal/10 text-signal-teal"
            : "border-signal-red/30 bg-signal-red/10 text-signal-red",
        )}
      >
        {report.verdict === "passed" ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
        <span className="font-medium">
          {report.verdict === "passed" ? "All tests passed" : "Tests failed"}
        </span>
      </div>

      {report.summary && (
        <div className="mb-4 flex items-start gap-2 rounded-md bg-surface-raised px-3 py-2 font-mono text-xs text-text-lo">
          <TerminalSquare size={14} className="mt-0.5 flex-shrink-0 text-text-faint" />
          <span className="whitespace-pre-wrap">{report.summary}</span>
        </div>
      )}

      {report.cases.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {report.cases.map((testCase, i) => (
            <li
              key={i}
              className="flex items-center gap-2 rounded-md border border-hairline px-3 py-2 font-mono text-xs"
            >
              {testCase.passed ? (
                <CheckCircle2 size={13} className="flex-shrink-0 text-signal-teal" />
              ) : (
                <XCircle size={13} className="flex-shrink-0 text-signal-red" />
              )}
              <span className="truncate text-text-hi">{testCase.name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
