import { useEffect } from "react";
import { useAppStore } from "./store/useAppStore";
import { TopBar } from "./components/layout/TopBar";
import { Dashboard } from "./pages/Dashboard";
import { Workspace } from "./pages/Workspace";

export default function App() {
  const theme = useAppStore((s) => s.theme);
  const activeProjectId = useAppStore((s) => s.activeProjectId);

  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  return (
    <div className="flex h-screen min-h-0 flex-col bg-ink text-text-hi">
      <TopBar />
      <main className="min-h-0 flex-1">
        {activeProjectId ? <Workspace /> : <Dashboard />}
      </main>
    </div>
  );
}
