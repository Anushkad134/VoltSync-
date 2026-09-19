import { ClerkProvider, SignedIn, SignedOut, RedirectToSignIn, useAuth } from "@clerk/clerk-react";
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "./contexts/ThemeContext";
import { apiClient } from "./lib/api";
import { useEffect, useState } from "react";

import AuthLayout from "./layouts/AuthLayout";
import DashboardLayout from "./layouts/DashboardLayout";
import SignInPage from "./pages/auth/SignInPage";
import SignUpPage from "./pages/auth/SignUpPage";
import RoleRouter from "./components/RoleRouter";
import RoleSelectionPage from "./pages/RoleSelectionPage";
import AiOrchestratorPage from "./pages/orchestrator/AiOrchestratorPage";

const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001/api/v1";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
});

// Component to handle initial role check after sign-in
function AuthHandler() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [checkingRole, setCheckingRole] = useState(true);

  useEffect(() => {
    apiClient.setTokenGetter(getToken);
  }, [getToken]);

  useEffect(() => {
    if (!isLoaded) return;

    if (isSignedIn) {
      const checkUserRole = async () => {
        try {
          const token = await getToken();
          if (!token) {
            setCheckingRole(false);
            return;
          }

          // Check if there is a pending role from pre-Clerk selection
          const pendingRole = localStorage.getItem("pendingRole");
          if (pendingRole) {
            try {
              await fetch(`${API_BASE_URL}/auth/me/role`, {
                method: "PUT",
                headers: {
                  "Content-Type": "application/json",
                  Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ role: pendingRole }),
              });
              localStorage.removeItem("pendingRole");
            } catch (err) {
              console.error("Error setting pending role:", err);
            }
          }

          // Fetch user role from backend
          const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          
          if (response.ok) {
            const data = await response.json();
            const userRole = data?.data?.role;
            
            // If user has no role or invalid role, redirect to role selection
            if (!userRole || userRole === "unassigned" || !["driver", "operator", "grid_operator"].includes(userRole)) {
              if (location.pathname === "/") {
                navigate("/role-selection", { replace: true });
              }
            } else {
              // User has a role, redirect to their dashboard if at root
              if (location.pathname === "/") {
                const targetPath = userRole === "grid_operator" ? "/grid-operator" : `/${userRole}`;
                navigate(targetPath, { replace: true });
              }
            }
          } else {
            if (location.pathname === "/") {
              navigate("/role-selection", { replace: true });
            }
          }
        } catch (error) {
          console.error("Error checking user role:", error);
          if (location.pathname === "/") {
            navigate("/role-selection", { replace: true });
          }
        } finally {
          setCheckingRole(false);
        }
      };

      checkUserRole();
    } else {
      setCheckingRole(false);
    }
  }, [isLoaded, isSignedIn, getToken, navigate, location.pathname]);

  if (!isLoaded || (checkingRole && location.pathname === "/")) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return null;
}

function AppContent() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/sign-in/*" element={<SignInPage />} />
        <Route path="/sign-up/*" element={<SignUpPage />} />
      </Route>

      <Route path="/role-selection" element={<RoleSelectionPage />} />

      <Route
        path="/*"
        element={
          <>
            <SignedIn>
              <AuthHandler />
              <DashboardLayout>
                <Routes>
                  <Route path="/" element={<Navigate to="/role-selection" replace />} />
                  <Route path="/driver/*" element={<RoleRouter role="driver" />} />
                  <Route path="/operator/*" element={<RoleRouter role="operator" />} />
                  <Route path="/grid-operator/*" element={<RoleRouter role="grid_operator" />} />
                  <Route path="/orchestrator" element={<AiOrchestratorPage />} />
                  <Route path="*" element={<Navigate to="/role-selection" replace />} />
                </Routes>
              </DashboardLayout>
            </SignedIn>
            <SignedOut>
              <Routes>
                <Route path="/" element={<Navigate to="/role-selection" replace />} />
                <Route path="*" element={<RedirectToSignIn />} />
              </Routes>
            </SignedOut>
          </>
        }
      />
    </Routes>
  );
}

function ClerkProviderWithRoutes() {
  const navigate = useNavigate();

  return (
    <ClerkProvider
      publishableKey={clerkPubKey}
      routerPush={(to) => navigate(to)}
      routerReplace={(to) => navigate(to, { replace: true })}
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
      signInFallbackRedirectUrl="/"
      signUpFallbackRedirectUrl="/"
    >
      <AppContent />
    </ClerkProvider>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark" storageKey="voltsync-theme">
        <Router>
          <ClerkProviderWithRoutes />
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
