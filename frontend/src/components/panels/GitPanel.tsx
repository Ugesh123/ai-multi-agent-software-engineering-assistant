import { useEffect, useState } from "react";
import { GitCommit as GitCommitIcon, Upload } from "lucide-react";
import { api } from "../../api/client";
import { EmptyState } from "./ReviewPanel";
import type { GitCommit } from "../../api/types";

export function GitPanel({ projectId }: { projectId: string }) {
  const [log, setLog] = useState<GitCommit[]>([]);
  const [loading, setLoading] = useState(true);
  const [remoteUrl, setRemoteUrl] = useState("");
  const [token, setToken] = useState("");
  const [pushing, setPushing] = useState(false);
  const [pushResult, setPushResult] = useState<{ success: boolean; message: string } | null>(null);

  const loadLog = async () => {
    setLoading(true);
    try {
      setLog(await api.getGitLog(projectId));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const handlePush = async () => {
    if (!remoteUrl.trim()) return;
    setPushing(true);
    setPushResult(null);
    try {
      await api.setGitRemote(projectId, remoteUrl.trim());
      const result = await api.pushToGit(projectId, remoteUrl.trim(), token.trim() || null);
      setPushResult({ success: result.success, message: result.output || "Pushed successfully." });
      setToken(""); // never keep the token around longer than needed
    } catch (err) {
      setPushResult({
        success: false,
        message: err instanceof Error ? err.message : "Push failed.",
      });
    } finally {
      setPushing(false);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4">
      <div className="mb-4 rounded-md border border-hairline bg-surface-raised p-3">
        <h3 className="mb-2 font-mono text-[10px] uppercase tracking-wider text-text-faint">
          Push to Remote
        </h3>
        <div className="flex flex-col gap-2">
          <input
            value={remoteUrl}
            onChange={(e) => setRemoteUrl(e.target.value)}
            placeholder="https://github.com/you/repo.git"
            className="rounded border border-hairline bg-ink px-2.5 py-1.5 text-xs text-text-hi placeholder:text-text-faint focus:border-signal-blue/50 focus:outline-none"
          />
          <input
            value={token}
            onChange={(e) => setToken(e.target.value)}
            type="password"
            placeholder="GitHub personal access token (not stored)"
            className="rounded border border-hairline bg-ink px-2.5 py-1.5 text-xs text-text-hi placeholder:text-text-faint focus:border-signal-blue/50 focus:outline-none"
          />
          <button
            onClick={handlePush}
            disabled={pushing || !remoteUrl.trim()}
            className="flex items-center justify-center gap-1.5 rounded-md bg-signal-blue px-3 py-1.5 text-xs font-medium text-ink disabled:opacity-40"
          >
            <Upload size={12} />
            {pushing ? "Pushing..." : "Push"}
          </button>
          {pushResult && (
            <p className={`text-[11px] ${pushResult.success ? "text-signal-teal" : "text-signal-red"}`}>
              {pushResult.message}
            </p>
          )}
          <p className="text-[10px] text-text-faint">
            The token is sent only for this push and is never saved on the server.
          </p>
        </div>
      </div>

      <h3 className="mb-2 font-mono text-[10px] uppercase tracking-wider text-text-faint">
        Commit History
      </h3>
      {loading && <p className="text-xs text-text-faint">Loading...</p>}
      {!loading && log.length === 0 && (
        <EmptyState message="No commits yet -- they're created automatically after each completed run." />
      )}
      <ul className="flex flex-col gap-2">
        {log.map((commit) => (
          <li key={commit.hash} className="rounded-md border border-hairline px-3 py-2">
            <div className="mb-1 flex items-center gap-2">
              <GitCommitIcon size={12} className="text-signal-amber" />
              <span className="font-mono text-[10px] text-text-faint">{commit.hash.slice(0, 8)}</span>
              <span className="ml-auto font-mono text-[10px] text-text-faint">
                {new Date(commit.date).toLocaleString()}
              </span>
            </div>
            <p className="text-xs text-text-hi">{commit.message}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
