import { UserButton } from "@clerk/clerk-react";
import { Zap, Settings, Sparkles } from "lucide-react";
import { ThemeToggle } from "../components/ThemeToggle";
import { Link } from "react-router-dom";
import { useState } from "react";
import { RoleSelector } from "../components/RoleSelector";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

export default function DashboardLayout({ children }) {
  const [showRoleSelector, setShowRoleSelector] = useState(false);
  const { data: user } = useQuery({
    queryKey: ["user-profile"],
    queryFn: authApi.getMe,
  });
  const queryClient = useQueryClient();

  const handleRoleChange = () => {
    queryClient.invalidateQueries();
    setShowRoleSelector(false);
    setTimeout(() => {
      window.location.href = "/";
    }, 500);
  };

  const roleLabels = {
    driver: "Driver",
    operator: "Operator",
    grid_operator: "Grid Operator",
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2">
            <Zap className="w-6 h-6 text-primary" />
            <span className="text-xl font-bold">VoltSync</span>
          </Link>

          <div className="flex items-center gap-3">
            <Link to="/orchestrator">
              <Button variant="outline" size="sm" className="flex items-center gap-1.5 border-emerald-500/40 text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 text-xs">
                <Sparkles className="w-3.5 h-3.5 animate-pulse" /> 3D AI Orchestrator
              </Button>
            </Link>

            {user && (
              <Badge variant="secondary" className="hidden sm:flex">
                {roleLabels[user.role] || user.role}
              </Badge>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowRoleSelector(!showRoleSelector)}
              title="Switch Role"
            >
              <Settings className="w-5 h-5" />
            </Button>
            <ThemeToggle />
            <UserButton afterSignOutUrl="/sign-in" />
          </div>
        </div>
      </header>

      {showRoleSelector && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="max-w-md w-full">
            <div className="mb-4 flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowRoleSelector(false)}
              >
                Close
              </Button>
            </div>
            <RoleSelector currentRole={user?.role || "driver"} onRoleChange={handleRoleChange} />
          </div>
        </div>
      )}

      <main className="container mx-auto px-4 py-8">{children}</main>
    </div>
  );
}
