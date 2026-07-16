import { useEffect, useState } from "react";
import { Download, Moon, Sun } from "lucide-react";
import clsx from "clsx";
import { api, downloadRunZip } from "../../api/client";
import { useAppStore } from "../../store/useAppStore";

export function TopBar() {
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const activeRun = useAppStore((s) => s.activeRun);

  const [health, setHealth] = useState<{ llm_provider: string; llm_healthy: boolean } | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const result = await api.health();
        if (!cancelled) setHealth(result);
      } catch {
        if (!cancelled) setHealth({ llm_provider: "unknown", llm_healthy: false });
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const canDownload = activeRun && activeRun.files.length > 0;

  const handleDownload = async () => {
    if (!activeRun) return;
    setDownloading(true);
    try {
      await downloadRunZip(activeRun.id);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <header className="flex h-12 flex-shrink-0 items-center justify-between border-b border-hairline bg-surface px-4">
      <div className="flex items-center gap-2 font-mono text-sm font-semibold tracking-tight text-text-hi">
        <span className="text-signal-blue">▍</span>
        Multi-Agent Coding Assistant
      </div>

      <div className="flex items-center gap-3">
        {health && (
          <div className="flex items-center gap-1.5 font-mono text-[11px] text-text-lo">
            <span
              className={clsx(
                "h-1.5 w-1.5 rounded-full",
                health.llm_healthy ? "bg-signal-teal" : "bg-signal-red",
              )}
            />
            {health.llm_provider}
          </div>
        )}

        <button
          type="button"
          onClick={handleDownload}
          disabled={!canDownload || downloading}
          title="Download generated project as .zip"
          className="flex items-center gap-1.5 rounded-md border border-hairline-strong px-2.5 py-1.5 text-xs text-text-lo transition-colors hover:border-signal-blue/50 hover:text-text-hi disabled:cursor-not-allowed disabled:opacity-30"
        >
          <Download size={13} />
          ZIP
        </button>

        <button
          type="button"
          onClick={toggleTheme}
          title="Toggle theme"
          className="flex h-7 w-7 items-center justify-center rounded-md border border-hairline-strong text-text-lo transition-colors hover:border-signal-blue/50 hover:text-text-hi"
        >
          {theme === "dark" ? <Sun size={13} /> : <Moon size={13} />}
        </button>
      </div>
    </header>
  );
}
