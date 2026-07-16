import type {
  AgentRun,
  ApiError,
  GitCommit,
  ModelListResponse,
  Project,
  ProjectDiff,
  ReferenceDocument,
  RetrievedChunk,
  StreamEvent,
} from "./types";

const BASE_URL = "/api/v1";

class ApiRequestError extends Error {
  status: number;
  details: Record<string, unknown>;

  constructor(message: string, status: number, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.details = details;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    let body: ApiError = { error: res.statusText, details: {} };
    try {
      body = await res.json();
    } catch {
      // Response wasn't JSON; fall back to statusText above.
    }
    throw new ApiRequestError(body.error, res.status, body.details);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; llm_provider: string; llm_healthy: boolean }>("/health"),

  listProjects: () => request<Project[]>("/projects"),

  createProject: (name: string, description = "") =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),

  getProject: (id: string) => request<Project>(`/projects/${id}`),

  updateProject: (id: string, patch: { name?: string; description?: string }) =>
    request<Project>(`/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  deleteProject: (id: string) => request<void>(`/projects/${id}`, { method: "DELETE" }),

  listRuns: (projectId: string) => request<AgentRun[]>(`/projects/${projectId}/runs`),

  createRun: (
    projectId: string,
    requestText: string,
    parentRunId?: string | null,
    model?: string | null,
  ) =>
    request<AgentRun>(`/projects/${projectId}/runs`, {
      method: "POST",
      body: JSON.stringify({ request: requestText, parent_run_id: parentRunId ?? null, model: model ?? null }),
    }),

  getRun: (runId: string) => request<AgentRun>(`/runs/${runId}`),

  getDiff: (runId: string, compareTo?: string | null) =>
    request<ProjectDiff>(
      `/runs/${runId}/diff${compareTo ? `?compare_to=${encodeURIComponent(compareTo)}` : ""}`,
    ),

  restoreVersion: (projectId: string, sourceRunId: string) =>
    request<AgentRun>(`/projects/${projectId}/runs/restore`, {
      method: "POST",
      body: JSON.stringify({ source_run_id: sourceRunId }),
    }),

  listDocuments: (projectId: string) =>
    request<ReferenceDocument[]>(`/projects/${projectId}/documents`),

  uploadDocument: async (projectId: string, file: File): Promise<ReferenceDocument> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${BASE_URL}/projects/${projectId}/documents`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({ error: res.statusText }))) as ApiError;
      throw new ApiRequestError(body.error, res.status, body.details);
    }
    return res.json();
  },

  deleteDocument: (projectId: string, documentId: string) =>
    request<void>(`/projects/${projectId}/documents/${documentId}`, { method: "DELETE" }),

  searchProjectContext: (projectId: string, query: string, topK = 5) =>
    request<RetrievedChunk[]>(
      `/projects/${projectId}/search?q=${encodeURIComponent(query)}&top_k=${topK}`,
    ),

  listModels: () => request<ModelListResponse>("/models"),

  getGitLog: (projectId: string) => request<GitCommit[]>(`/projects/${projectId}/git/log`),

  setGitRemote: (projectId: string, remoteUrl: string) =>
    request<void>(`/projects/${projectId}/git/remote`, {
      method: "POST",
      body: JSON.stringify({ remote_url: remoteUrl }),
    }),

  pushToGit: (projectId: string, remoteUrl: string, token: string | null, branch = "main") =>
    request<{ success: boolean; output: string }>(`/projects/${projectId}/git/push`, {
      method: "POST",
      body: JSON.stringify({ remote_url: remoteUrl, token, branch }),
    }),
};

export { ApiRequestError };

/** Triggers a browser download of the run's generated files as a .zip. */
export async function downloadRunZip(runId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/runs/${runId}/download`);
  if (!res.ok) {
    const body = (await res.json().catch(() => ({ error: res.statusText }))) as ApiError;
    throw new ApiRequestError(body.error, res.status, body.details);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match?.[1] ?? `project-${runId.slice(0, 8)}.zip`;

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/**
 * Consumes the backend's SSE stream for a run, invoking `onEvent` for every
 * `data:` frame. Returns a function to abort the stream early (e.g. if the
 * user navigates away). Implemented over `fetch` + `ReadableStream` rather
 * than the native `EventSource` so we get a definite "done" signal and can
 * cancel it cleanly.
 */
export function streamRun(
  runId: string,
  onEvent: (event: StreamEvent) => void,
  onDone: () => void,
  onError: (message: string) => void,
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE_URL}/runs/${runId}/stream`, {
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = (await res.json().catch(() => ({ error: res.statusText }))) as ApiError;
        onError(body.error ?? `Stream failed with status ${res.status}`);
        return;
      }
      if (!res.body) {
        onError("Streaming is not supported by this browser/response.");
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const isDone = frame.startsWith("event: done");
          const dataLine = frame.split("\n").find((l) => l.startsWith("data: "));
          if (!dataLine) continue;

          const payload = dataLine.slice("data: ".length).trim();
          if (isDone || payload === "{}") {
            onDone();
            continue;
          }
          if (payload) {
            onEvent(JSON.parse(payload) as StreamEvent);
          }
        }
      }
      onDone();
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      onError(err instanceof Error ? err.message : "Unknown streaming error");
    }
  })();

  return () => controller.abort();
}
