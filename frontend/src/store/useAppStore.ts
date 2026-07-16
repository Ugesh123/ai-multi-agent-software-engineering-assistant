import { create } from "zustand";
import { api, streamRun } from "../api/client";
import type { AgentRun, Project, StreamEvent } from "../api/types";

export type Theme = "dark" | "light";

interface AppState {
  // Projects
  projects: Project[];
  projectsLoading: boolean;
  activeProjectId: string | null;
  searchQuery: string;

  // Runs (history for the active project)
  runsByProject: Record<string, AgentRun[]>;
  activeRunId: string | null;
  activeRun: AgentRun | null;
  isStreaming: boolean;
  streamLog: StreamEvent[];
  streamError: string | null;

  // File explorer / editor
  selectedFilePath: string | null;
  expandedDirs: Set<string>;

  // Edit mode: when set, the next run submitted will pass this as parent_run_id
  // so the Coder agent edits that run's existing files incrementally.
  editingFromRun: AgentRun | null;

  // Version comparison: up to 2 run ids selected from history for side-by-side diff.
  compareSelection: string[];

  // Multi-model: optional per-run model override (e.g. "llama3" or "anthropic:claude-sonnet-4-5").
  selectedModel: string | null;

  // Theme
  theme: Theme;

  // Actions
  loadProjects: () => Promise<void>;
  createProject: (name: string, description?: string) => Promise<Project>;
  renameProject: (id: string, name: string) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  setActiveProject: (id: string | null) => Promise<void>;
  setSearchQuery: (q: string) => void;

  loadRunsForProject: (projectId: string) => Promise<void>;
  startRun: (projectId: string, request: string) => Promise<void>;
  openRun: (runId: string) => Promise<void>;
  cancelStream: () => void;
  restoreVersion: (projectId: string, sourceRunId: string) => Promise<void>;

  selectFile: (path: string | null) => void;
  toggleDir: (path: string) => void;

  startEditingFrom: (run: AgentRun) => void;
  cancelEditingFrom: () => void;

  toggleCompareSelection: (runId: string) => void;
  clearCompareSelection: () => void;

  setSelectedModel: (model: string | null) => void;

  toggleTheme: () => void;
}

let stopStreamFn: (() => void) | null = null;

const THEME_STORAGE_KEY = "maca:theme";

function loadInitialTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  return stored === "light" ? "light" : "dark";
}

export const useAppStore = create<AppState>((set, get) => ({
  projects: [],
  projectsLoading: false,
  activeProjectId: null,
  searchQuery: "",

  runsByProject: {},
  activeRunId: null,
  activeRun: null,
  isStreaming: false,
  streamLog: [],
  streamError: null,

  selectedFilePath: null,
  expandedDirs: new Set(),

  editingFromRun: null,
  compareSelection: [],
  selectedModel: null,

  theme: loadInitialTheme(),

  loadProjects: async () => {
    set({ projectsLoading: true });
    try {
      const projects = await api.listProjects();
      set({ projects, projectsLoading: false });
    } catch {
      set({ projectsLoading: false });
    }
  },

  createProject: async (name, description = "") => {
    const project = await api.createProject(name, description);
    set((state) => ({ projects: [project, ...state.projects] }));
    return project;
  },

  renameProject: async (id, name) => {
    const updated = await api.updateProject(id, { name });
    set((state) => ({
      projects: state.projects.map((p) => (p.id === id ? updated : p)),
    }));
  },

  deleteProject: async (id) => {
    await api.deleteProject(id);
    set((state) => ({
      projects: state.projects.filter((p) => p.id !== id),
      activeProjectId: state.activeProjectId === id ? null : state.activeProjectId,
      activeRunId: state.activeProjectId === id ? null : state.activeRunId,
      activeRun: state.activeProjectId === id ? null : state.activeRun,
    }));
  },

  setActiveProject: async (id) => {
    get().cancelStream();
    set({
      activeProjectId: id,
      activeRunId: null,
      activeRun: null,
      selectedFilePath: null,
      streamLog: [],
      streamError: null,
      editingFromRun: null,
    });
    if (id) {
      await get().loadRunsForProject(id);
    }
  },

  setSearchQuery: (q) => set({ searchQuery: q }),

  loadRunsForProject: async (projectId) => {
    const runs = await api.listRuns(projectId);
    set((state) => ({ runsByProject: { ...state.runsByProject, [projectId]: runs } }));
  },

  startRun: async (projectId, request) => {
    const parentRunId = get().editingFromRun?.id ?? null;
    const model = get().selectedModel;
    const run = await api.createRun(projectId, request, parentRunId, model);
    set((state) => ({
      activeRunId: run.id,
      activeRun: run,
      streamLog: [],
      streamError: null,
      isStreaming: true,
      editingFromRun: null,
      runsByProject: {
        ...state.runsByProject,
        [projectId]: [run, ...(state.runsByProject[projectId] ?? [])],
      },
    }));

    stopStreamFn?.();
    stopStreamFn = streamRun(
      run.id,
      (event) => {
        set((state) => ({
          streamLog: [...state.streamLog, event],
        }));
      },
      async () => {
        set({ isStreaming: false });
        const fresh = await api.getRun(run.id);
        set((state) => ({
          activeRun: state.activeRunId === run.id ? fresh : state.activeRun,
          runsByProject: {
            ...state.runsByProject,
            [projectId]: (state.runsByProject[projectId] ?? []).map((r) =>
              r.id === fresh.id ? fresh : r,
            ),
          },
        }));
      },
      (message) => {
        set({ isStreaming: false, streamError: message });
      },
    );
  },

  openRun: async (runId) => {
    get().cancelStream();
    const run = await api.getRun(runId);
    set({
      activeRunId: run.id,
      activeRun: run,
      selectedFilePath: run.files[0]?.path ?? null,
      isStreaming: false,
      streamLog: [],
      streamError: null,
      editingFromRun: null,
    });
  },

  cancelStream: () => {
    stopStreamFn?.();
    stopStreamFn = null;
  },

  restoreVersion: async (projectId, sourceRunId) => {
    const restored = await api.restoreVersion(projectId, sourceRunId);
    set((state) => ({
      activeRunId: restored.id,
      activeRun: restored,
      selectedFilePath: restored.files[0]?.path ?? null,
      isStreaming: false,
      streamLog: [],
      streamError: null,
      editingFromRun: null,
      runsByProject: {
        ...state.runsByProject,
        [projectId]: [restored, ...(state.runsByProject[projectId] ?? [])],
      },
    }));
  },

  selectFile: (path) => set({ selectedFilePath: path }),

  toggleDir: (path) =>
    set((state) => {
      const next = new Set(state.expandedDirs);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return { expandedDirs: next };
    }),

  startEditingFrom: (run) => set({ editingFromRun: run }),
  cancelEditingFrom: () => set({ editingFromRun: null }),

  toggleCompareSelection: (runId) =>
    set((state) => {
      if (state.compareSelection.includes(runId)) {
        return { compareSelection: state.compareSelection.filter((id) => id !== runId) };
      }
      // Keep at most 2: drop the oldest selection when adding a third.
      const next = [...state.compareSelection, runId];
      return { compareSelection: next.length > 2 ? next.slice(-2) : next };
    }),
  clearCompareSelection: () => set({ compareSelection: [] }),

  setSelectedModel: (model) => set({ selectedModel: model }),

  toggleTheme: () =>
    set((state) => {
      const next: Theme = state.theme === "dark" ? "light" : "dark";
      if (typeof window !== "undefined") {
        window.localStorage.setItem(THEME_STORAGE_KEY, next);
      }
      return { theme: next };
    }),
}));
