import { useState } from "react";
import { ArrowLeft, Check, GitBranch, History, Pencil, RotateCcw, Trash2, X } from "lucide-react";
import clsx from "clsx";
import { useAppStore } from "../../store/useAppStore";
import { statusLabel } from "../../lib/pipeline";

interface WorkspaceSidebarProps {
  /** Mobile-only: renders as a fixed slide-over with a scrim, closable via onClose. */
  mobileOpen?: boolean;
  onClose?: () => void;
}

export function WorkspaceSidebar({ mobileOpen = false, onClose }: WorkspaceSidebarProps) {
  const activeProjectId = useAppStore((s) => s.activeProjectId);
  const projects = useAppStore((s) => s.projects);
  const runsByProject = useAppStore((s) => s.runsByProject);
  const activeRunId = useAppStore((s) => s.activeRunId);
  const setActiveProject = useAppStore((s) => s.setActiveProject);
  const renameProject = useAppStore((s) => s.renameProject);
  const deleteProject = useAppStore((s) => s.deleteProject);
  const openRun = useAppStore((s) => s.openRun);
  const startEditingFrom = useAppStore((s) => s.startEditingFrom);
  const restoreVersion = useAppStore((s) => s.restoreVersion);
  const compareSelection = useAppStore((s) => s.compareSelection);
  const toggleCompareSelection = useAppStore((s) => s.toggleCompareSelection);

  const project = projects.find((p) => p.id === activeProjectId);
  const runs = activeProjectId ? runsByProject[activeProjectId] ?? [] : [];

  const [renaming, setRenaming] = useState(false);
  const [nameDraft, setNameDraft] = useState(project?.name ?? "");

  if (!project) return null;

  const startRename = () => {
    setNameDraft(project.name);
    setRenaming(true);
  };

  const commitRename = async () => {
    const trimmed = nameDraft.trim();
    if (trimmed && trimmed !== project.name) {
      await renameProject(project.id, trimmed);
    }
    setRenaming(false);
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete project "${project.name}"? This cannot be undone.`)) return;
    await deleteProject(project.id);
  };

  const handleRestore = async (e: React.MouseEvent, run: (typeof runs)[number]) => {
    e.stopPropagation();
    if (!window.confirm(`Restore v${run.version}? This creates a new version with v${run.version}'s files.`)) return;
    await restoreVersion(project.id, run.id);
  };

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={clsx(
          "z-50 flex w-64 flex-shrink-0 flex-col border-r border-hairline bg-surface transition-transform duration-200",
          "fixed inset-y-0 left-0 md:static md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        <div className="flex items-center justify-between border-b border-hairline p-3 md:hidden">
          <span className="font-mono text-xs uppercase tracking-wider text-text-faint">Project</span>
          <button onClick={onClose} className="text-text-faint hover:text-text-hi">
            <X size={16} />
          </button>
        </div>
        <div className="border-b border-hairline p-3">
        <button
          type="button"
          onClick={() => setActiveProject(null)}
          className="mb-3 flex items-center gap-1.5 text-xs text-text-lo hover:text-text-hi"
        >
          <ArrowLeft size={13} />
          All projects
        </button>

        {renaming ? (
          <div className="flex items-center gap-1">
            <input
              autoFocus
              value={nameDraft}
              onChange={(e) => setNameDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitRename();
                if (e.key === "Escape") setRenaming(false);
              }}
              className="min-w-0 flex-1 rounded border border-signal-blue/50 bg-ink px-2 py-1 text-sm text-text-hi focus:outline-none"
            />
            <button onClick={commitRename} className="text-signal-teal">
              <Check size={15} />
            </button>
            <button onClick={() => setRenaming(false)} className="text-text-faint">
              <X size={15} />
            </button>
          </div>
        ) : (
          <div className="group flex items-center gap-1.5">
            <h2 className="truncate text-sm font-semibold text-text-hi" title={project.name}>
              {project.name}
            </h2>
            <button
              onClick={startRename}
              className="text-text-faint opacity-0 transition-opacity group-hover:opacity-100 hover:text-text-hi"
              title="Rename project"
            >
              <Pencil size={12} />
            </button>
            <button
              onClick={handleDelete}
              className="ml-auto text-text-faint opacity-0 transition-opacity group-hover:opacity-100 hover:text-signal-red"
              title="Delete project"
            >
              <Trash2 size={12} />
            </button>
          </div>
        )}
        {project.description && (
          <p className="mt-1 line-clamp-2 text-xs text-text-faint">{project.description}</p>
        )}
        </div>

        <div className="flex items-center justify-between px-3 pt-3">
          <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-text-faint">
            <History size={12} />
            History
          </div>
          {compareSelection.length > 0 && (
            <span className="font-mono text-[10px] text-signal-blue">
              {compareSelection.length}/2 selected
            </span>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-2">
        {runs.length === 0 && (
          <p className="px-2 py-3 text-xs text-text-faint">No runs yet for this project.</p>
        )}
        <ul className="flex flex-col gap-1">
          {runs.map((run) => {
            const isCompleted = run.status === "completed";
            const isSelectedForCompare = compareSelection.includes(run.id);
            return (
              <li key={run.id}>
                <div
                  className={clsx(
                    "group flex flex-col gap-1 rounded-md px-2.5 py-2 transition-colors",
                    run.id === activeRunId
                      ? "bg-signal-blue/15"
                      : "hover:bg-surface-raised",
                  )}
                >
                  <button
                    onClick={() => {
                      openRun(run.id);
                      onClose?.();
                    }}
                    className="flex w-full items-start gap-1.5 text-left"
                  >
                    {isCompleted && (
                      <input
                        type="checkbox"
                        checked={isSelectedForCompare}
                        onClick={(e) => e.stopPropagation()}
                        onChange={() => toggleCompareSelection(run.id)}
                        title="Select to compare"
                        className="mt-1 flex-shrink-0 accent-signal-blue"
                      />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="flex-shrink-0 rounded bg-hairline-strong px-1.5 py-0.5 font-mono text-[10px] font-semibold text-text-hi">
                          v{run.version}
                        </span>
                        <span
                          className={clsx(
                            "font-mono text-[10px]",
                            run.status === "completed" && "text-signal-teal",
                            run.status === "failed" && "text-signal-red",
                            run.status !== "completed" && run.status !== "failed" && "text-signal-amber",
                          )}
                        >
                          {statusLabel(run.status)}
                        </span>
                      </div>
                      <p
                        className={clsx(
                          "mt-1 line-clamp-2 text-xs leading-snug",
                          run.id === activeRunId ? "text-text-hi" : "text-text-lo",
                        )}
                      >
                        {run.commit_message || run.request}
                      </p>
                      <p className="mt-0.5 font-mono text-[9px] text-text-faint">
                        {new Date(run.created_at).toLocaleString()}
                      </p>
                    </div>
                  </button>

                  {isCompleted && (
                    <div className="flex items-center gap-2 pl-1 opacity-0 transition-opacity group-hover:opacity-100">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          startEditingFrom(run);
                          onClose?.();
                        }}
                        className="flex items-center gap-1 text-[10px] text-text-faint hover:text-signal-blue"
                        title="Edit this version"
                      >
                        <GitBranch size={11} />
                        Edit
                      </button>
                      <button
                        onClick={(e) => handleRestore(e, run)}
                        className="flex items-center gap-1 text-[10px] text-text-faint hover:text-signal-amber"
                        title="Restore this version"
                      >
                        <RotateCcw size={11} />
                        Restore
                      </button>
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
        </div>
      </aside>
    </>
  );
}
