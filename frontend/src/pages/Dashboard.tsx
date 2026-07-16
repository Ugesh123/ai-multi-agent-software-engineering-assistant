import { useEffect, useMemo, useState } from "react";
import { FolderGit2, Plus, Search, Trash2 } from "lucide-react";
import { useAppStore } from "../store/useAppStore";
import type { Project } from "../api/types";

export function Dashboard() {
  const projects = useAppStore((s) => s.projects);
  const projectsLoading = useAppStore((s) => s.projectsLoading);
  const loadProjects = useAppStore((s) => s.loadProjects);
  const createProject = useAppStore((s) => s.createProject);
  const deleteProject = useAppStore((s) => s.deleteProject);
  const setActiveProject = useAppStore((s) => s.setActiveProject);
  const searchQuery = useAppStore((s) => s.searchQuery);
  const setSearchQuery = useAppStore((s) => s.setSearchQuery);

  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return projects;
    return projects.filter(
      (p) => p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q),
    );
  }, [projects, searchQuery]);

  const handleCreate = async () => {
    const trimmed = newName.trim();
    if (!trimmed) return;
    const project = await createProject(trimmed, newDescription.trim());
    setNewName("");
    setNewDescription("");
    setCreating(false);
    await setActiveProject(project.id);
  };

  const handleDelete = async (e: React.MouseEvent, project: Project) => {
    e.stopPropagation();
    if (!window.confirm(`Delete project "${project.name}"? This cannot be undone.`)) return;
    await deleteProject(project.id);
  };

  return (
    <div className="mx-auto flex h-full max-w-4xl flex-col px-6 py-10">
      <div className="mb-8">
        <h1 className="font-mono text-2xl font-semibold text-text-hi">Projects</h1>
        <p className="mt-1 text-sm text-text-lo">
          Describe a feature and watch six agents plan, design, build, review, test, and document it.
        </p>
      </div>

      <div className="mb-6 flex items-center gap-3">
        <div className="flex flex-1 items-center gap-2 rounded-md border border-hairline-strong bg-surface px-3 py-2">
          <Search size={15} className="text-text-faint" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search projects..."
            className="flex-1 bg-transparent text-sm text-text-hi placeholder:text-text-faint focus:outline-none"
          />
        </div>
        <button
          type="button"
          onClick={() => setCreating((v) => !v)}
          className="flex items-center gap-1.5 rounded-md bg-signal-blue px-3.5 py-2 text-sm font-medium text-ink hover:opacity-90"
        >
          <Plus size={15} />
          New project
        </button>
      </div>

      {creating && (
        <div className="mb-6 flex flex-col gap-2 rounded-md border border-hairline-strong bg-surface p-4">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Project name"
            className="rounded border border-hairline bg-ink px-3 py-2 text-sm text-text-hi placeholder:text-text-faint focus:border-signal-blue/50 focus:outline-none"
          />
          <input
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
            placeholder="Description (optional)"
            className="rounded border border-hairline bg-ink px-3 py-2 text-sm text-text-hi placeholder:text-text-faint focus:border-signal-blue/50 focus:outline-none"
          />
          <div className="flex justify-end gap-2 pt-1">
            <button
              onClick={() => setCreating(false)}
              className="rounded-md px-3 py-1.5 text-xs text-text-lo hover:text-text-hi"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={!newName.trim()}
              className="rounded-md bg-signal-blue px-3.5 py-1.5 text-xs font-medium text-ink disabled:opacity-40"
            >
              Create
            </button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {projectsLoading && <p className="text-sm text-text-faint">Loading projects...</p>}

        {!projectsLoading && filtered.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-16 text-center">
            <FolderGit2 size={28} className="text-text-faint" />
            <p className="text-sm text-text-faint">
              {projects.length === 0 ? "No projects yet. Create your first one above." : "No projects match your search."}
            </p>
          </div>
        )}

        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {filtered.map((project) => (
            <li key={project.id}>
              <button
                onClick={() => setActiveProject(project.id)}
                className="group flex w-full flex-col items-start gap-1 rounded-md border border-hairline bg-surface p-4 text-left transition-colors hover:border-signal-blue/40"
              >
                <div className="flex w-full items-start justify-between gap-2">
                  <h3 className="truncate font-mono text-sm font-semibold text-text-hi">{project.name}</h3>
                  <span
                    onClick={(e) => handleDelete(e, project)}
                    className="flex-shrink-0 text-text-faint opacity-0 transition-opacity hover:text-signal-red group-hover:opacity-100"
                    title="Delete project"
                  >
                    <Trash2 size={13} />
                  </span>
                </div>
                <p className="line-clamp-2 text-xs text-text-lo">
                  {project.description || "No description"}
                </p>
                <p className="mt-1 font-mono text-[10px] text-text-faint">
                  Updated {new Date(project.updated_at).toLocaleDateString()}
                </p>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
