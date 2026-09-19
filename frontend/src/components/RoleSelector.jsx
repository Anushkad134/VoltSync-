import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/Card";
import { Button } from "./ui/Button";
import { Select } from "./ui/Select";
import { Label } from "./ui/Label";
import { Input } from "./ui/Input";
import { UserCog, Zap, Building2, Network } from "lucide-react";

const roleInfo = {
  driver: {
    icon: Zap,
    title: "Driver",
    description: "Find stations and manage charging sessions",
    color: "text-emerald-500",
  },
  operator: {
    icon: Building2,
    title: "Station Operator",
    description: "Monitor station fleet and manage operations",
    color: "text-blue-500",
  },
  grid_operator: {
    icon: Network,
    title: "Grid Operator",
    description: "Monitor regional grid and renewable integration",
    color: "text-cyan-500",
  },
};

export function RoleSelector({ currentRole, onRoleChange }) {
  const [selectedRole, setSelectedRole] = useState(currentRole);
  const [region, setRegion] = useState("Region_A");
  const [stationIds, setStationIds] = useState("STATION_001,STATION_002");
  const queryClient = useQueryClient();

  const updateRoleMutation = useMutation({
    mutationFn: (data) => apiClient.put("/auth/me/role", data),
    onSuccess: () => {
      queryClient.invalidateQueries(["user-profile"]);
      if (onRoleChange) {
        onRoleChange();
      }
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const data = {
      role: selectedRole,
      region: selectedRole === "grid_operator" ? region : null,
      linked_station_ids: selectedRole === "operator" ? stationIds.split(",").map(s => s.trim()) : [],
    };
    updateRoleMutation.mutate(data);
  };

  const RoleIcon = roleInfo[selectedRole]?.icon || UserCog;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <UserCog className="w-5 h-5 text-primary" />
          <CardTitle>Switch Role</CardTitle>
        </div>
        <CardDescription>Change your role to test different dashboards</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="role">Select Role</Label>
            <Select
              id="role"
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
            >
              <option value="driver">Driver</option>
              <option value="operator">Station Operator</option>
              <option value="grid_operator">Grid Operator</option>
            </Select>
          </div>

          <div className="p-4 bg-accent rounded-lg">
            <div className="flex items-start gap-3">
              <RoleIcon className={`w-6 h-6 ${roleInfo[selectedRole]?.color} mt-0.5`} />
              <div>
                <div className="font-medium">{roleInfo[selectedRole]?.title}</div>
                <div className="text-sm text-muted-foreground mt-1">
                  {roleInfo[selectedRole]?.description}
                </div>
              </div>
            </div>
          </div>

          {selectedRole === "grid_operator" && (
            <div className="space-y-2">
              <Label htmlFor="region">Region</Label>
              <Select
                id="region"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
              >
                <option value="Region_A">Region A</option>
                <option value="Region_B">Region B</option>
                <option value="Region_C">Region C</option>
              </Select>
            </div>
          )}

          {selectedRole === "operator" && (
            <div className="space-y-2">
              <Label htmlFor="stations">Linked Station IDs (comma-separated)</Label>
              <Input
                id="stations"
                value={stationIds}
                onChange={(e) => setStationIds(e.target.value)}
                placeholder="STATION_001,STATION_002"
              />
              <div className="text-xs text-muted-foreground">
                Separate multiple station IDs with commas
              </div>
            </div>
          )}

          <Button
            type="submit"
            disabled={updateRoleMutation.isPending}
            className="w-full"
          >
            {updateRoleMutation.isPending ? "Updating..." : "Update Role"}
          </Button>

          {updateRoleMutation.isSuccess && (
            <div className="text-sm text-emerald-600 dark:text-emerald-400 text-center">
              Role updated successfully! Redirecting...
            </div>
          )}

          {updateRoleMutation.isError && (
            <div className="text-sm text-destructive text-center">
              {updateRoleMutation.error.message}
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
