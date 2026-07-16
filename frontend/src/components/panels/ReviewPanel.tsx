import { AlertTriangle, CheckCircle2 } from "lucide-react";
import clsx from "clsx";
import type { Review } from "../../api/types";

const SEVERITY_STYLES: Record<string, string> = {
  blocker: "text-signal-red border-signal-red/30 bg-signal-red/10",
  major: "text-signal-amber border-signal-amber/30 bg-signal-amber/10",
  minor: "text-signal-blue border-signal-blue/30 bg-signal-blue/10",
  nit: "text-text-lo border-hairline-strong bg-surface-raised",
};

export function ReviewPanel({ review }: { review: Review | null }) {
  if (!review) {
    return <EmptyState message="No review yet. Runs generate a review after the Coder step." />;
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4">
      <div
        className={clsx(
          "mb-4 flex items-center gap-2 rounded-md border px-3 py-2 text-sm",
          review.verdict === "approved"
            ? "border-signal-teal/30 bg-signal-teal/10 text-signal-teal"
            : "border-signal-amber/30 bg-signal-amber/10 text-signal-amber",
        )}
      >
        {review.verdict === "approved" ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
        <span className="font-medium">
          {review.verdict === "approved" ? "Approved" : "Changes requested"}
        </span>
      </div>

      {review.summary && <p className="mb-4 text-sm leading-relaxed text-text-lo">{review.summary}</p>}

      {review.findings.length > 0 && (
        <ul className="flex flex-col gap-2">
          {review.findings.map((finding, i) => (
            <li
              key={i}
              className={clsx("rounded-md border px-3 py-2 text-xs", SEVERITY_STYLES[finding.severity])}
            >
              <div className="mb-1 flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider">
                <span>{finding.severity}</span>
                <span className="text-text-faint">·</span>
                <span className="truncate text-text-lo">{finding.file_path}</span>
                {finding.line != null && <span className="text-text-faint">:{finding.line}</span>}
              </div>
              <p className="text-text-hi/90">{finding.message}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex h-full items-center justify-center px-6 text-center">
      <p className="max-w-xs text-xs text-text-faint">{message}</p>
    </div>
  );
}
