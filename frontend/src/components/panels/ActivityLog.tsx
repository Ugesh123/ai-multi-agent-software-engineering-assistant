import { useEffect, useRef } from "react";
import { Bot } from "lucide-react";
import { PIPELINE_STAGES } from "../../lib/pipeline";
import type { StreamEvent } from "../../api/types";

const ROLE_COLOR: Record<string, string> = Object.fromEntries(
  PIPELINE_STAGES.map((s) => [s.key, s.color]),
);

export function ActivityLog({ events }: { events: StreamEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [events.length]);

  const withMessages = events.filter((e) => e.latest_message);

  if (withMessages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center">
        <p className="max-w-xs text-xs text-text-faint">
          Agent activity will appear here once a run starts.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-2 overflow-y-auto p-4">
      {withMessages.map((event, i) => {
        const message = event.latest_message!;
        const color = ROLE_COLOR[message.role] ?? "var(--color-signal-blue)";
        return (
          <div key={message.id ?? i} className="flex gap-2.5 rounded-md border border-hairline px-3 py-2">
            <div
              className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full"
              style={{ backgroundColor: `${color}22`, color }}
            >
              <Bot size={12} />
            </div>
            <div className="min-w-0">
              <div className="font-mono text-[10px] uppercase tracking-wider" style={{ color }}>
                {message.role}
              </div>
              <p className="mt-0.5 break-words text-xs leading-relaxed text-text-lo">
                {message.content}
              </p>
            </div>
          </div>
        );
      })}
      <div ref={endRef} />
    </div>
  );
}
