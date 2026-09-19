import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { RoleSelector } from "../components/RoleSelector";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/Card";
import { Zap } from "lucide-react";

export default function WelcomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const handleRoleChange = () => {
    // Invalidate queries and redirect
    queryClient.invalidateQueries();
    setTimeout(() => {
      navigate("/", { replace: true });
      window.location.reload();
    }, 1000);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-2xl w-full space-y-6">
        <Card className="border-primary/20">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <div className="p-3 bg-primary/10 rounded-full">
                <Zap className="w-12 h-12 text-primary" />
              </div>
            </div>
            <CardTitle className="text-3xl">Welcome to VoltSync!</CardTitle>
            <CardDescription className="text-base">
              Smart EV Charging Optimization Platform
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="prose dark:prose-invert max-w-none mb-6">
              <p className="text-center text-muted-foreground">
                You've successfully signed in. Before you begin, please select your role to access
                the appropriate dashboard and features.
              </p>
            </div>
          </CardContent>
        </Card>

        <RoleSelector currentRole="driver" onRoleChange={handleRoleChange} />

        <div className="text-center text-sm text-muted-foreground">
          <p>You can change your role anytime from the settings menu</p>
        </div>
      </div>
    </div>
  );
}
