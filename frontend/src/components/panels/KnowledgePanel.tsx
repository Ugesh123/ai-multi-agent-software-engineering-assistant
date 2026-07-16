import { useEffect, useRef, useState } from "react";
import { FileText, Search, Trash2, Upload } from "lucide-react";
import { api } from "../../api/client";
import { EmptyState } from "./ReviewPanel";
import type { ReferenceDocument, RetrievedChunk } from "../../api/types";

export function KnowledgePanel({ projectId }: { projectId: string }) {
  const [documents, setDocuments] = useState<ReferenceDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RetrievedChunk[] | null>(null);
  const [searching, setSearching] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      setDocuments(await api.listDocuments(projectId));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await api.uploadDocument(projectId, file);
      await loadDocuments();
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (docId: string) => {
    await api.deleteDocument(projectId, docId);
    await loadDocuments();
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      setResults(await api.searchProjectContext(projectId, query));
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4">
      <div className="mb-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-faint">
            Reference Documents
          </h3>
          <label className="flex cursor-pointer items-center gap-1.5 rounded-md border border-hairline-strong px-2.5 py-1.5 text-xs text-text-lo hover:border-signal-blue/50 hover:text-text-hi">
            <Upload size={12} />
            {uploading ? "Uploading..." : "Upload"}
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.pdf"
              className="hidden"
              disabled={uploading}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleUpload(file);
              }}
            />
          </label>
        </div>

        {loading && <p className="text-xs text-text-faint">Loading...</p>}
        {!loading && documents.length === 0 && (
          <p className="text-xs text-text-faint">
            No reference documents yet. Upload a spec (.txt, .md, .pdf) to ground the Planner and
            Architect agents in it.
          </p>
        )}
        <ul className="flex flex-col gap-1.5">
          {documents.map((doc) => (
            <li
              key={doc.id}
              className="group flex items-start gap-2 rounded-md border border-hairline px-3 py-2"
            >
              <FileText size={13} className="mt-0.5 flex-shrink-0 text-signal-blue" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-medium text-text-hi">{doc.filename}</p>
                <p className="mt-0.5 line-clamp-1 text-[11px] text-text-faint">{doc.preview}</p>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                className="flex-shrink-0 text-text-faint opacity-0 transition-opacity hover:text-signal-red group-hover:opacity-100"
              >
                <Trash2 size={12} />
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="border-t border-hairline pt-4">
        <h3 className="mb-2 font-mono text-[10px] uppercase tracking-wider text-text-faint">
          Search Knowledge
        </h3>
        <div className="mb-3 flex items-center gap-2">
          <div className="flex flex-1 items-center gap-2 rounded-md border border-hairline-strong bg-ink px-2.5 py-1.5">
            <Search size={13} className="text-text-faint" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search reference docs + generated code..."
              className="flex-1 bg-transparent text-xs text-text-hi placeholder:text-text-faint focus:outline-none"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={searching || !query.trim()}
            className="rounded-md bg-signal-blue px-3 py-1.5 text-xs font-medium text-ink disabled:opacity-40"
          >
            Search
          </button>
        </div>

        {results !== null && results.length === 0 && (
          <EmptyState message="No matching content found." />
        )}
        {results !== null && results.length > 0 && (
          <ul className="flex flex-col gap-2">
            {results.map((chunk, i) => (
              <li key={i} className="rounded-md border border-hairline px-3 py-2">
                <div className="mb-1 flex items-center gap-2 font-mono text-[10px] text-text-faint">
                  <span
                    className={
                      chunk.source_type === "reference_doc" ? "text-signal-blue" : "text-signal-amber"
                    }
                  >
                    {chunk.source_type === "reference_doc" ? "doc" : "code"}
                  </span>
                  <span className="truncate">{chunk.source_label}</span>
                  <span className="ml-auto">{(chunk.score * 100).toFixed(0)}%</span>
                </div>
                <p className="line-clamp-3 whitespace-pre-wrap text-xs text-text-lo">{chunk.content}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
