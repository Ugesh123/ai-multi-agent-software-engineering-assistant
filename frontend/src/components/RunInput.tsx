import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";

interface RunInputProps {
  onSubmit: (request: string) => void;
  disabled: boolean;
  placeholder?: string;
}

export function RunInput({ onSubmit, disabled, placeholder }: RunInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  return (
    <div className="flex items-end gap-2 border-b border-hairline bg-surface px-4 py-3">
      <div className="flex flex-1 items-start gap-2 rounded-md border border-hairline-strong bg-ink px-3 py-2 focus-within:border-signal-blue/60">
        <Sparkles size={15} className="mt-1 flex-shrink-0 text-signal-blue" />
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder={placeholder ?? "Describe what to build... e.g. 'a CLI todo app with add/list/done commands'"}
          rows={1}
          disabled={disabled}
          className="max-h-32 min-h-[24px] flex-1 resize-none bg-transparent text-sm text-text-hi placeholder:text-text-faint focus:outline-none disabled:opacity-50"
        />
      </div>
      <button
        type="button"
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
        className="flex h-[38px] items-center gap-2 rounded-md bg-signal-blue px-4 text-sm font-medium text-ink transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {disabled ? <Loader2 size={14} className="animate-spin" /> : null}
        {disabled ? "Running" : "Run"}
      </button>
    </div>
  );
}
