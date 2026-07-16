import { ChevronRight, File, FolderClosed, FolderOpen } from "lucide-react";
import clsx from "clsx";
import { buildFileTree, type FileTreeNode } from "../../lib/fileTree";
import { useAppStore } from "../../store/useAppStore";
import type { GeneratedFile } from "../../api/types";

interface FileExplorerProps {
  files: GeneratedFile[];
}

export function FileExplorer({ files }: FileExplorerProps) {
  const tree = buildFileTree(files);

  if (files.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
        <FolderClosed size={22} className="text-text-faint" />
        <p className="text-xs text-text-faint">No files yet. Run a request to generate some.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto py-2">
      <div className="mb-1 px-3 font-mono text-[10px] uppercase tracking-wider text-text-faint">
        Explorer
      </div>
      <TreeLevel nodes={tree} depth={0} />
    </div>
  );
}

function TreeLevel({ nodes, depth }: { nodes: FileTreeNode[]; depth: number }) {
  return (
    <ul>
      {nodes.map((node) => (
        <TreeRow key={node.path} node={node} depth={depth} />
      ))}
    </ul>
  );
}

function TreeRow({ node, depth }: { node: FileTreeNode; depth: number }) {
  const expandedDirs = useAppStore((s) => s.expandedDirs);
  const toggleDir = useAppStore((s) => s.toggleDir);
  const selectedFilePath = useAppStore((s) => s.selectedFilePath);
  const selectFile = useAppStore((s) => s.selectFile);

  const isDir = node.type === "dir";
  // Directories default open unless explicitly collapsed.
  const isOpen = isDir && !expandedDirs.has(node.path) ? true : expandedDirs.has(node.path);
  const isSelected = node.path === selectedFilePath;

  return (
    <li>
      <button
        type="button"
        onClick={() => (isDir ? toggleDir(node.path) : selectFile(node.path))}
        style={{ paddingLeft: `${depth * 14 + 10}px` }}
        className={clsx(
          "flex w-full items-center gap-1.5 py-1 pr-2 text-left text-[13px] transition-colors",
          isSelected
            ? "bg-signal-blue/15 text-text-hi"
            : "text-text-lo hover:bg-surface-raised hover:text-text-hi",
        )}
        title={node.path}
      >
        {isDir ? (
          <>
            <ChevronRight
              size={13}
              className={clsx("flex-shrink-0 text-text-faint transition-transform", isOpen && "rotate-90")}
            />
            {isOpen ? (
              <FolderOpen size={14} className="flex-shrink-0 text-signal-blue" />
            ) : (
              <FolderClosed size={14} className="flex-shrink-0 text-signal-blue" />
            )}
          </>
        ) : (
          <>
            <span className="w-[13px] flex-shrink-0" />
            <File size={14} className="flex-shrink-0 text-text-faint" />
          </>
        )}
        <span className="truncate">{node.name}</span>
        {node.file?.change_type === "update" && (
          <span className="ml-auto flex-shrink-0 text-[10px] font-semibold text-signal-amber">M</span>
        )}
      </button>
      {isDir && isOpen && <TreeLevel nodes={node.children} depth={depth + 1} />}
    </li>
  );
}
