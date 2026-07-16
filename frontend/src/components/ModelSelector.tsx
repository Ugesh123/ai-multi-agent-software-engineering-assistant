import { useEffect, useState } from "react";
import { Cpu } from "lucide-react";
import { api } from "../api/client";
import { useAppStore } from "../store/useAppStore";
import type { ModelInfo } from "../api/types";

export function ModelSelector() {
  const selectedModel = useAppStore((s) => s.selectedModel);
  const setSelectedModel = useAppStore((s) => s.setSelectedModel);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [defaultModel, setDefaultModel] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    api
      .listModels()
      .then((res) => {
        if (cancelled) return;
        setModels(res.models);
        setDefaultModel(res.current_default);
      })
      .catch(() => {
        // Model listing is best-effort; the run input still works with the default.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (models.length <= 1) {
    return null; // Nothing meaningful to choose between.
  }

  return (
    <div className="flex items-center gap-1.5 px-4 pb-2">
      <Cpu size={12} className="text-text-faint" />
      <select
        value={selectedModel ?? ""}
        onChange={(e) => setSelectedModel(e.target.value || null)}
        className="rounded border border-hairline bg-surface px-2 py-1 font-mono text-[11px] text-text-lo focus:border-signal-blue/50 focus:outline-none"
        title="Model for this run (default: configured backend model)"
      >
        <option value="">Default ({defaultModel})</option>
        {models.map((m) => (
          <option key={m.name} value={m.provider === "anthropic" ? m.name : m.name}>
            {m.name} ({m.provider})
          </option>
        ))}
      </select>
    </div>
  );
}
