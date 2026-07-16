import { describe, expect, it } from "vitest";
import { buildFileTree, languageForPath } from "../fileTree";
import type { GeneratedFile } from "../../api/types";

function file(path: string, content = ""): GeneratedFile {
  return { path, content, change_type: "create", language: "text" };
}

describe("buildFileTree", () => {
  it("builds a nested tree from flat paths", () => {
    const tree = buildFileTree([file("app/core.py"), file("app/cli.py"), file("README.md")]);

    const names = tree.map((n) => n.name).sort();
    expect(names).toEqual(["README.md", "app"]);

    const appNode = tree.find((n) => n.name === "app")!;
    expect(appNode.type).toBe("dir");
    expect(appNode.children.map((c) => c.name).sort()).toEqual(["cli.py", "core.py"]);
  });

  it("sorts directories before files, alphabetically within each group", () => {
    const tree = buildFileTree([file("b.py"), file("a.py"), file("zdir/x.py"), file("adir/y.py")]);
    expect(tree.map((n) => n.name)).toEqual(["adir", "zdir", "a.py", "b.py"]);
  });

  it("excludes files marked as deleted", () => {
    const files: GeneratedFile[] = [
      file("keep.py"),
      { path: "gone.py", content: "x", change_type: "delete", language: "python" },
    ];
    const tree = buildFileTree(files);
    expect(tree.map((n) => n.name)).toEqual(["keep.py"]);
  });

  it("handles deeply nested paths", () => {
    const tree = buildFileTree([file("a/b/c/d.py")]);
    let node = tree[0];
    const pathParts: string[] = [];
    while (node) {
      pathParts.push(node.name);
      node = node.children[0];
    }
    expect(pathParts).toEqual(["a", "b", "c", "d.py"]);
  });

  it("returns an empty tree for no files", () => {
    expect(buildFileTree([])).toEqual([]);
  });

  it("attaches the GeneratedFile object to leaf nodes only", () => {
    const tree = buildFileTree([file("app/core.py")]);
    const dirNode = tree[0];
    const fileNode = dirNode.children[0];
    expect(dirNode.file).toBeUndefined();
    expect(fileNode.file).toBeDefined();
    expect(fileNode.file!.path).toBe("app/core.py");
  });
});

describe("languageForPath", () => {
  it("maps common extensions to their language", () => {
    expect(languageForPath("app/core.py")).toBe("python");
    expect(languageForPath("src/index.ts")).toBe("typescript");
    expect(languageForPath("src/App.tsx")).toBe("typescript");
    expect(languageForPath("README.md")).toBe("markdown");
    expect(languageForPath("config.json")).toBe("json");
  });

  it("falls back to plaintext for unknown extensions", () => {
    expect(languageForPath("Makefile")).toBe("plaintext");
    expect(languageForPath("data.xyz")).toBe("plaintext");
  });

  it("is case-insensitive on extension", () => {
    expect(languageForPath("Script.PY")).toBe("python");
  });
});
