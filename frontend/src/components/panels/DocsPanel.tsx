import { EmptyState } from "./ReviewPanel";

export function DocsPanel({ documentation }: { documentation: string }) {
  if (!documentation) {
    return <EmptyState message="No documentation yet. The Documentation agent runs last." />;
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <article className="max-w-2xl">
        {documentation.split("\n").map((line, i) => (
          <MarkdownLine key={i} line={line} />
        ))}
      </article>
    </div>
  );
}

/** Minimal, dependency-free markdown line renderer -- headings, bullets,
 * fenced code blocks, and plain paragraphs. Kept intentionally small since
 * the README content is plain and generated, not arbitrary user markdown. */
function MarkdownLine({ line }: { line: string }) {
  if (line.startsWith("### ")) {
    return <h3 className="mb-2 mt-4 font-mono text-sm font-semibold text-text-hi">{line.slice(4)}</h3>;
  }
  if (line.startsWith("## ")) {
    return <h2 className="mb-2 mt-5 font-mono text-base font-semibold text-text-hi">{line.slice(3)}</h2>;
  }
  if (line.startsWith("# ")) {
    return <h1 className="mb-3 font-mono text-lg font-semibold text-text-hi">{line.slice(2)}</h1>;
  }
  if (line.startsWith("```")) {
    return <div className="my-1 border-t border-dashed border-hairline-strong" />;
  }
  if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
    return (
      <li className="ml-4 list-disc text-sm leading-relaxed text-text-lo">{line.trim().slice(2)}</li>
    );
  }
  if (!line.trim()) {
    return <div className="h-2" />;
  }
  return <p className="text-sm leading-relaxed text-text-lo">{line}</p>;
}
