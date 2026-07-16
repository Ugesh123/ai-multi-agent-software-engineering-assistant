import { useState } from "react";
import clsx from "clsx";
import { AlertCircle, GitCompare, PanelLeft, X } from "lucide-react";
import { useAppStore } from "../store/useAppStore";
import { WorkspaceSidebar } from "../components/layout/WorkspaceSidebar";
import { PipelineRail } from "../components/pipeline/PipelineRail";
import { RunInput } from "../components/RunInput";
import { FileExplorer } from "../components/files/FileExplorer";
import { CodeEditor } from "../components/files/CodeEditor";
import { PlanPanel } from "../components/panels/PlanPanel";
import { ReviewPanel } from "../components/panels/ReviewPanel";
import { TestsPanel } from "../components/panels/TestsPanel";
import { DocsPanel } from "../components/panels/DocsPanel";
import { ActivityLog } from "../components/panels/ActivityLog";
import { DiffPanel } from "../components/panels/DiffPanel";
import { KnowledgePanel } from "../components/panels/KnowledgePanel";
import { GitPanel } from "../components/panels/GitPanel";
import { ModelSelector } from "../components/ModelSelector";

type Tab = "files" | "plan" | "review" | "tests" | "docs" | "activity" | "diff" | "knowledge" | "git";

const TABS: { key: Tab; label: string }[] = [
  { key: "files", label: "Files" },
  { key: "plan", label: "Plan" },
  { key: "review", label: "Review" },
  { key: "tests", label: "Tests" },
  { key: "docs", label: "Docs" },
  { key: "diff", label: "Diff" },
  { key: "knowledge", label: "Knowledge" },
  { key: "git", label: "Git" },
  { key: "activity", label: "Activity" },
];

export function Workspace() {
  const activeProjectId = useAppStore((s) => s.activeProjectId);
  const activeRun = useAppStore((s) => s.activeRun);
  const isStreaming = useAppStore((s) => s.isStreaming);
  const streamError = useAppStore((s) => s.streamError);
  const streamLog = useAppStore((s) => s.streamLog);
  const startRun = useAppStore((s) => s.startRun);
  const editingFromRun = useAppStore((s) => s.editingFromRun);
  const cancelEditingFrom = useAppStore((s) => s.cancelEditingFrom);
  const compareSelection = useAppStore((s) => s.compareSelection);
  const clearCompareSelection = useAppStore((s) => s.clearCompareSelection);
  const runsByProject = useAppStore((s) => s.runsByProject);

  const [tab, setTab] = useState<Tab>("activity");
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  if (!activeProjectId) return null;

  const handleSubmit = async (request: string) => {
    setTab("activity");
    await startRun(activeProjectId, request);
  };

  const files = activeRun?.files ?? [];

  const runs = activeProjectId ? runsByProject[activeProjectId] ?? [] : [];
  const compareRuns = compareSelection
    .map((id) => runs.find((r) => r.id === id))
    .filter((r): r is NonNullable<typeof r> => Boolean(r))
    .sort((a, b) => a.version - b.version);
  const comparePair =
    compareRuns.length === 2 ? { baseline: compareRuns[0], target: compareRuns[1] } : null;

  return (
    <div className="flex h-full min-h-0">
      <WorkspaceSidebar
        mobileOpen={mobileSidebarOpen}
        onClose={() => setMobileSidebarOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-hairline bg-surface px-2 md:hidden">
          <button
            onClick={() => setMobileSidebarOpen(true)}
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center text-text-lo hover:text-text-hi"
          >
            <PanelLeft size={16} />
          </button>
        </div>

        {editingFromRun && (
          <div className="flex items-center gap-2 border-b border-hairline bg-signal-blue/10 px-4 py-1.5 text-xs text-signal-blue">
            <span>
              Editing from v{editingFromRun.version} — your next request will modify its files.
            </span>
            <button onClick={cancelEditingFrom} className="ml-auto text-text-faint hover:text-text-hi">
              <X size={13} />
            </button>
          </div>
        )}

        {compareSelection.length > 0 && (
          <div className="flex items-center gap-2 border-b border-hairline bg-surface-raised px-4 py-1.5 text-xs text-text-lo">
            <GitCompare size={13} className="text-signal-blue" />
            {comparePair ? (
              <button
                onClick={() => setTab("diff")}
                className="text-signal-blue hover:underline"
              >
                Compare v{comparePair.baseline.version} → v{comparePair.target.version}
              </button>
            ) : (
              <span>Select one more version to compare ({compareSelection.length}/2)</span>
            )}
            <button onClick={clearCompareSelection} className="ml-auto text-text-faint hover:text-text-hi">
              <X size={13} />
            </button>
          </div>
        )}

        <RunInput
          onSubmit={handleSubmit}
          disabled={isStreaming}
          placeholder={
            editingFromRun
              ? `Describe your change to v${editingFromRun.version}... e.g. 'add input validation'`
              : undefined
          }
        />
        <ModelSelector />

        <div className="border-b border-hairline bg-surface px-4 py-2.5">
          {activeRun ? (
            <PipelineRail
              status={activeRun.status}
              reviewIterations={activeRun.review_iterations}
              testIterations={activeRun.test_iterations}
            />
          ) : (
            <p className="py-2 text-xs text-text-faint">
              Start a run above to see the agent pipeline in action.
            </p>
          )}
          {streamError && (
            <div className="mt-2 flex items-center gap-1.5 rounded-md border border-signal-red/30 bg-signal-red/10 px-2.5 py-1.5 text-xs text-signal-red">
              <AlertCircle size={13} />
              {streamError}
            </div>
          )}
        </div>

        <div className="flex flex-shrink-0 gap-1 border-b border-hairline bg-surface px-4">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={clsx(
                "border-b-2 px-3 py-2 font-mono text-xs uppercase tracking-wide transition-colors",
                tab === t.key
                  ? "border-signal-blue text-text-hi"
                  : "border-transparent text-text-faint hover:text-text-lo",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="min-h-0 flex-1">
          {tab === "files" && (
            <div className="flex h-full">
              <div className="w-64 flex-shrink-0 border-r border-hairline">
                <FileExplorer files={files} />
              </div>
              <div className="min-w-0 flex-1">
                <CodeEditor files={files} />
              </div>
            </div>
          )}
          {tab === "plan" && <PlanPanel plan={activeRun?.plan ?? []} />}
          {tab === "review" && <ReviewPanel review={activeRun?.review ?? null} />}
          {tab === "tests" && <TestsPanel report={activeRun?.test_report ?? null} />}
          {tab === "docs" && <DocsPanel documentation={activeRun?.documentation ?? ""} />}
          {tab === "diff" &&
            (comparePair ? (
              <DiffPanel targetRunId={comparePair.target.id} baselineRunId={comparePair.baseline.id} />
            ) : activeRun ? (
              <DiffPanel targetRunId={activeRun.id} />
            ) : (
              <div className="flex h-full items-center justify-center px-6 text-center">
                <p className="max-w-xs text-xs text-text-faint">
                  Select a run, or check two versions in History to compare them.
                </p>
              </div>
            ))}
          {tab === "activity" && <ActivityLog events={streamLog} />}
          {tab === "knowledge" && activeProjectId && <KnowledgePanel projectId={activeProjectId} />}
          {tab === "git" && activeProjectId && <GitPanel projectId={activeProjectId} />}
        </div>
      </div>
    </div>
  );
}
