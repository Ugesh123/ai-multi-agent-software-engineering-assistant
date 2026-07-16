import { ListChecks } from "lucide-react";
import type { PlanItem } from "../../api/types";
import { EmptyState } from "./ReviewPanel";

export function PlanPanel({ plan }: { plan: PlanItem[] }) {
  if (plan.length === 0) {
    return <EmptyState message="No plan yet. The Planner agent runs first." />;
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      <ol className="flex flex-col gap-2">
        {plan
          .slice()
          .sort((a, b) => a.order - b.order)
          .map((item) => (
            <li key={item.id} className="rounded-md border border-hairline bg-surface-raised px-3 py-2.5">
              <div className="flex items-start gap-2">
                <ListChecks size={14} className="mt-0.5 flex-shrink-0 text-signal-blue" />
                <div>
                  <p className="text-sm font-medium text-text-hi">{item.title}</p>
                  {item.description && (
                    <p className="mt-0.5 text-xs leading-relaxed text-text-lo">{item.description}</p>
                  )}
                </div>
              </div>
            </li>
          ))}
      </ol>
    </div>
  );
}
