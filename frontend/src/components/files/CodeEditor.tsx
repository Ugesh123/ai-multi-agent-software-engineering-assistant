import Editor, { type OnMount } from "@monaco-editor/react";
import { FileCode2 } from "lucide-react";
import { useAppStore } from "../../store/useAppStore";
import { languageForPath } from "../../lib/fileTree";
import type { GeneratedFile } from "../../api/types";

interface CodeEditorProps {
  files: GeneratedFile[];
}

export function CodeEditor({ files }: CodeEditorProps) {
  const selectedFilePath = useAppStore((s) => s.selectedFilePath);
  const theme = useAppStore((s) => s.theme);

  const activeFile = files.find((f) => f.path === selectedFilePath);

  const handleMount: OnMount = (_editor, monaco) => {
    monaco.editor.defineTheme("maca-console", {
      base: "vs-dark",
      inherit: true,
      rules: [],
      colors: {
        "editor.background": "#12151c",
        "editor.lineHighlightBackground": "#171b2440",
        "editorLineNumber.foreground": "#5b6377",
        "editorLineNumber.activeForeground": "#8891a6",
        "editorGutter.background": "#12151c",
        "editorCursor.foreground": "#4f9dff",
      },
    });
    monaco.editor.setTheme("maca-console");
  };

  if (!activeFile) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 bg-surface text-center">
        <FileCode2 size={26} className="text-text-faint" />
        <p className="text-xs text-text-faint">Select a file from the explorer to view it</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-hairline bg-surface px-4 py-2 font-mono text-xs text-text-lo">
        <FileCode2 size={13} className="text-signal-blue" />
        {activeFile.path}
      </div>
      <div className="min-h-0 flex-1">
        <Editor
          key={activeFile.path}
          path={activeFile.path}
          language={languageForPath(activeFile.path)}
          value={activeFile.content}
          theme={theme === "dark" ? "maca-console" : "light"}
          onMount={handleMount}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 13,
            fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
            lineNumbers: "on",
            renderLineHighlight: "line",
            scrollBeyondLastLine: false,
            padding: { top: 12 },
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  );
}
