import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Zap, User, Settings, Activity, Loader2 } from "lucide-react";
import { useAuth } from "@clerk/clerk-react";
import { useState } from "react";

export default function RoleSelectionPage() {
  const navigate = useNavigate();
  const { isSignedIn, isLoaded, getToken } = useAuth();
  const [loadingRole, setLoadingRole] = useState(null);

  const handleRoleSelect = async (role) => {
    setLoadingRole(role);
    localStorage.setItem("pendingRole", role);

    if (isSignedIn) {
      try {
        const token = await getToken();
        if (token) {
          await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://localhost:8001/api/v1"}/auth/me/role`, {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ role }),
          });
          localStorage.removeItem("pendingRole");
        }
      } catch (err) {
        console.error("Error updating role:", err);
      }
      const targetPath = role === "grid_operator" ? "/grid-operator" : `/${role}`;
      navigate(targetPath, { replace: true });
    } else {
      // Direct redirect to Clerk Sign-In / Login page
      navigate("/sign-in");
    }
  };

  if (!isLoaded) return null;

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="max-w-4xl w-full space-y-8">
        <div className="text-center space-y-2">
          <div className="flex justify-center mb-6">
            <div className="p-4 bg-primary/10 rounded-full">
              <Zap className="w-12 h-12 text-primary" />
            </div>
          </div>
          <h1 className="text-4xl font-bold tracking-tight">Welcome to VoltSync</h1>
          <p className="text-xl text-muted-foreground">Select your role to get started</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <Card 
            className="hover:border-primary/50 transition-colors cursor-pointer flex flex-col justify-between" 
            onClick={() => handleRoleSelect("driver")}
          >
            <CardHeader className="text-center">
              <User className="w-12 h-12 mx-auto text-blue-500 mb-4" />
              <CardTitle>Driver</CardTitle>
              <CardDescription>Find stations and optimize charging</CardDescription>
            </CardHeader>
            <CardContent>
              <Button 
                className="w-full pointer-events-none" 
                variant="outline"
                disabled={loadingRole !== null}
              >
                {loadingRole === "driver" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Select Driver
              </Button>
            </CardContent>
          </Card>

          <Card 
            className="hover:border-primary/50 transition-colors cursor-pointer flex flex-col justify-between" 
            onClick={() => handleRoleSelect("operator")}
          >
            <CardHeader className="text-center">
              <Settings className="w-12 h-12 mx-auto text-emerald-500 mb-4" />
              <CardTitle>Operator</CardTitle>
              <CardDescription>Manage your charging stations</CardDescription>
            </CardHeader>
            <CardContent>
              <Button 
                className="w-full pointer-events-none" 
                variant="outline"
                disabled={loadingRole !== null}
              >
                {loadingRole === "operator" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Select Operator
              </Button>
            </CardContent>
          </Card>

          <Card 
            className="hover:border-primary/50 transition-colors cursor-pointer flex flex-col justify-between" 
            onClick={() => handleRoleSelect("grid_operator")}
          >
            <CardHeader className="text-center">
              <Activity className="w-12 h-12 mx-auto text-amber-500 mb-4" />
              <CardTitle>Grid Operator</CardTitle>
              <CardDescription>Monitor grid load and curtailment</CardDescription>
            </CardHeader>
            <CardContent>
              <Button 
                className="w-full pointer-events-none" 
                variant="outline"
                disabled={loadingRole !== null}
              >
                {loadingRole === "grid_operator" ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Select Grid Operator
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

