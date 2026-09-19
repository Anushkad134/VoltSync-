import { useQuery } from "@tanstack/react-query";
import { authApi } from "../lib/api";
import { Routes, Route, Navigate } from "react-router-dom";
import DriverDashboard from "../pages/driver/DriverDashboard";
import StationDiscovery from "../pages/driver/StationDiscovery";
import ActiveSession from "../pages/driver/ActiveSession";
import OperatorDashboard from "../pages/operator/OperatorDashboard";
import GridOperatorDashboard from "../pages/grid-operator/GridOperatorDashboard";
import WelcomePage from "../pages/WelcomePage";

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
    </div>
  );
}

function ErrorDisplay({ error }) {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-destructive mb-2">Error Loading Profile</h2>
        <p className="text-muted-foreground">{error.message}</p>
      </div>
    </div>
  );
}

export default function RoleRouter({ role: forcedRole, showWelcome }) {
  const { data: user, isLoading, error } = useQuery({
    queryKey: ["user-profile"],
    queryFn: authApi.getMe,
    staleTime: 300000, // 5 minutes
    retry: 1,
  });

  if (isLoading) {
    return <LoadingSpinner />;
  }

  // If there's an error (e.g., no role assigned yet), show welcome/role selection
  if (error || !user?.role) {
    return <WelcomePage />;
  }

  // Show welcome page for new users if explicitly requested
  if (showWelcome) {
    return <WelcomePage />;
  }

  const userRole = forcedRole || user?.role || "driver";

  // Route to appropriate dashboard based on role
  if (!forcedRole) {
    if (userRole === "driver") {
      return <Navigate to="/driver" replace />;
    } else if (userRole === "operator") {
      return <Navigate to="/operator" replace />;
    } else if (userRole === "grid_operator") {
      return <Navigate to="/grid-operator" replace />;
    }
  }

  // Render role-specific routes
  if (userRole === "driver") {
    return (
      <Routes>
        <Route index element={<DriverDashboard />} />
        <Route path="stations" element={<StationDiscovery />} />
        <Route path="session/:sessionId" element={<ActiveSession />} />
      </Routes>
    );
  }

  if (userRole === "operator") {
    return (
      <Routes>
        <Route index element={<OperatorDashboard />} />
      </Routes>
    );
  }

  if (userRole === "grid_operator") {
    return (
      <Routes>
        <Route index element={<GridOperatorDashboard />} />
      </Routes>
    );
  }

  return <Navigate to="/" replace />;
}
