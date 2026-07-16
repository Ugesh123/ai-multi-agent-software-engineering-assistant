import type { GeneratedFile } from "../api/types";

export interface FileTreeNode {
  name: string;
  path: string;
  type: "file" | "dir";
  children: FileTreeNode[];
  file?: GeneratedFile;
}

export function buildFileTree(files: GeneratedFile[]): FileTreeNode[] {
  const root: FileTreeNode[] = [];

  const sorted = [...files]
    .filter((f) => f.change_type !== "delete")
    .sort((a, b) => a.path.localeCompare(b.path));

  for (const file of sorted) {
    const parts = file.path.split("/").filter(Boolean);
    let siblings = root;
    let currentPath = "";

    parts.forEach((part, i) => {
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isLeaf = i === parts.length - 1;

      let node = siblings.find((n) => n.name === part);
      if (!node) {
        node = {
          name: part,
          path: currentPath,
          type: isLeaf ? "file" : "dir",
          children: [],
          file: isLeaf ? file : undefined,
        };
        siblings.push(node);
      }
      siblings = node.children;
    });
  }

  sortTree(root);
  return root;
}

function sortTree(nodes: FileTreeNode[]): void {
  nodes.sort((a, b) => {
    if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  for (const node of nodes) {
    if (node.children.length) sortTree(node.children);
  }
}

const EXTENSION_LANGUAGE: Record<string, string> = {
  py: "python",
  ts: "typescript",
  tsx: "typescript",
  js: "javascript",
  jsx: "javascript",
  json: "json",
  md: "markdown",
  yml: "yaml",
  yaml: "yaml",
  toml: "toml",
  html: "html",
  css: "css",
  sh: "shell",
  txt: "plaintext",
};

export function languageForPath(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  return EXTENSION_LANGUAGE[ext] ?? "plaintext";
}
