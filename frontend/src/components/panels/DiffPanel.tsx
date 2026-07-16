import { useEffect, useState } from "react";
import { DiffEditor } from "@monaco-editor/react";
import { ChevronDown, ChevronRight, FileMinus, FilePlus, FileText, GitCompare } from "lucide-react";
import clsx from "clsx";
import { api } from "../../api/client";
import { useAppStore } from "../../store/useAppStore";
import { languageForPath } from "../../lib/fileTree";
import { EmptyState } from "./ReviewPanel";
import type { AgentRun, ProjectDiff } from "../../api/types";

interface DiffPanelProps {
  targetRunId: string;
  /** Explicit baseline to compare against (e.g. from a 2-version selection).
   * Falls back to the target run's parent if omitted. */
  baselineRunId?: string | null;
}

export function DiffPanel({ targetRunId, baselineRunId }: DiffPanelProps) {
  const theme = useAppStore((s) => s.theme);
  const [diff, setDiff] = useState<ProjectDiff | null>(null);
  const [targetRun, setTargetRun] = useState<AgentRun | null>(null);
  const [baselineRun, setBaselineRun] = useState<AgentRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPath, setExpandedPath] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const target = await api.getRun(targetRunId);
        const resolvedBaselineId = baselineRunId ?? target.parent_run_id;
        const [diffResult, baseline] = await Promise.all([
          api.getDiff(targetRunId, baselineRunId ?? undefined),
          resolvedBaselineId ? api.getRun(resolvedBaselineId) : Promise.resolve(null),
        ]);
        if (cancelled) return;
        setTargetRun(target);
        setBaselineRun(baseline);
        setDiff(diffResult);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load diff");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [targetRunId, baselineRunId]);

  if (loading) {
    return <EmptyState message="Loading diff..." />;
  }
  if (error) {
    return <EmptyState message={error} />;
  }
  if (!diff || !targetRun) {
    return <EmptyState message="No diff available." />;
  }
  if (!baselineRun) {
    return (
      <EmptyState message="This is the first version -- nothing to compare against yet. All files are new." />
    );
  }
  if (!diff.added.length && !diff.deleted.length && !diff.modified.length) {
    return <EmptyState message="No differences between these two versions." />;
  }

  const contentFor = (run: AgentRun, path: string) =>
    run.files.find((f) => f.path === path)?.content ?? "";

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="flex items-center gap-2 border-b border-hairline bg-surface-raised px-4 py-2 font-mono text-xs text-text-lo">
        <GitCompare size={13} className="text-signal-blue" />
        Comparing v{baselineRun.version} → v{targetRun.version}
      </div>

      <div className="flex flex-col gap-3 p-4">
        {diff.added.length > 0 && (
          <DiffSection title="Added" count={diff.added.length} color="var(--color-signal-teal)">
            {diff.added.map((path) => (
              <FileRow key={path} path={path} icon={<FilePlus size={13} />} color="text-signal-teal" />
            ))}
          </DiffSection>
        )}

        {diff.deleted.length > 0 && (
          <DiffSection title="Deleted" count={diff.deleted.length} color="var(--color-signal-red)">
            {diff.deleted.map((path) => (
              <FileRow key={path} path={path} icon={<FileMinus size={13} />} color="text-signal-red" />
            ))}
          </DiffSection>
        )}

        {diff.modified.length > 0 && (
          <DiffSection title="Modified" count={diff.modified.length} color="var(--color-signal-amber)">
            {diff.modified.map((m) => {
              const isExpanded = expandedPath === m.path;
              return (
                <div key={m.path} className="overflow-hidden rounded-md border border-hairline">
                  <button
                    onClick={() => setExpandedPath(isExpanded ? null : m.path)}
                    className="flex w-full items-center gap-2 bg-surface-raised px-3 py-2 text-left text-xs hover:bg-hairline/30"
                  >
                    {isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                    <FileText size={13} className="text-signal-amber" />
                    <span className="flex-1 truncate text-text-hi">{m.path}</span>
                    <span className="font-mono text-[10px] text-signal-teal">+{m.added_lines}</span>
                    <span className="font-mono text-[10px] text-signal-red">-{m.removed_lines}</span>
                  </button>
                  {isExpanded && (
                    <div className="h-80 border-t border-hairline">
                      <DiffEditor
                        original={contentFor(baselineRun, m.path)}
                        modified={contentFor(targetRun, m.path)}
                        language={languageForPath(m.path)}
                        theme={theme === "dark" ? "vs-dark" : "light"}
                        options={{
                          readOnly: true,
                          minimap: { enabled: false },
                          fontSize: 12,
                          renderSideBySide: true,
                          scrollBeyondLastLine: false,
                        }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </DiffSection>
        )}
      </div>
    </div>
  );
}

function DiffSection({
  title,
  count,
  color,
  children,
}: {
  title: string;
  count: number;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div
        className="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider"
        style={{ color }}
      >
        {title}
        <span className="rounded-full bg-surface-raised px-1.5 text-text-lo">{count}</span>
      </div>
      <div className="flex flex-col gap-1.5">{children}</div>
    </div>
  );
}

function FileRow({ path, icon, color }: { path: string; icon: React.ReactNode; color: string }) {
  return (
    <div className={clsx("flex items-center gap-2 rounded-md border border-hairline px-3 py-1.5 text-xs", color)}>
      {icon}
      <span className="truncate text-text-hi">{path}</span>
    </div>
  );
}
