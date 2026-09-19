import { useQuery } from "@tanstack/react-query";
import { operatorApi } from "../../lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { StatusBadge } from "../../components/StatusBadge";
import {
  Activity,
  Zap,
  AlertTriangle,
  TrendingUp,
  Server,
  Users,
  Battery,
  Clock,
} from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

function StationCard({ station }) {
  const healthColor =
    station.status === "ONLINE"
      ? "text-emerald-500"
      : station.status === "DEGRADED"
      ? "text-yellow-500"
      : "text-red-500";

  const healthVariant =
    station.status === "ONLINE"
      ? "success"
      : station.status === "DEGRADED"
      ? "warning"
      : "destructive";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">{station.name}</CardTitle>
            <CardDescription>{station.location}</CardDescription>
          </div>
          <Badge variant={healthVariant}>{station.status}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Active Sessions</div>
            <div className="text-2xl font-bold flex items-center gap-2">
              <Users className="w-5 h-5 text-primary" />
              {station.active_sessions || 0}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-sm text-muted-foreground">Power Draw</div>
            <div className="text-2xl font-bold flex items-center gap-2">
              <Zap className="w-5 h-5 text-primary" />
              {station.current_power_draw?.toFixed(1) || 0} kW
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Utilization</span>
            <span className="font-medium">
              {station.total_ports - station.available_ports}/{station.total_ports} ports
            </span>
          </div>
          <div className="w-full bg-secondary rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all"
              style={{
                width: `${((station.total_ports - station.available_ports) / station.total_ports) * 100}%`,
              }}
            />
          </div>
        </div>

        <div className="pt-2 border-t">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Power Limit</span>
            <span className="font-medium">{station.max_power_kw} kW</span>
          </div>
          <div className="flex items-center justify-between text-sm mt-1">
            <span className="text-muted-foreground">Queue Length</span>
            <span className="font-medium">{station.queue_length || 0}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function QueueTable({ sessions }) {
  if (!sessions || sessions.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Clock className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>No queued sessions</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th className="text-left py-3 px-4 font-medium text-sm text-muted-foreground">
              Session ID
            </th>
            <th className="text-left py-3 px-4 font-medium text-sm text-muted-foreground">
              Status
            </th>
            <th className="text-left py-3 px-4 font-medium text-sm text-muted-foreground">
              Target SOC
            </th>
            <th className="text-left py-3 px-4 font-medium text-sm text-muted-foreground">
              Queue Position
            </th>
            <th className="text-left py-3 px-4 font-medium text-sm text-muted-foreground">
              Est. Wait Time
            </th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((session, idx) => (
            <tr key={session.id} className="border-b hover:bg-accent transition-colors">
              <td className="py-3 px-4 font-mono text-sm">{session.id.slice(0, 8)}...</td>
              <td className="py-3 px-4">
                <StatusBadge status={session.status} />
              </td>
              <td className="py-3 px-4">
                <div className="flex items-center gap-1">
                  <Battery className="w-4 h-4 text-muted-foreground" />
                  {session.target_soc}%
                </div>
              </td>
              <td className="py-3 px-4 font-medium">{idx + 1}</td>
              <td className="py-3 px-4 text-muted-foreground">
                {session.estimated_wait_minutes
                  ? `${session.estimated_wait_minutes} min`
                  : "N/A"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PowerConsumptionChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>No power consumption data</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis dataKey="time" className="text-xs" />
        <YAxis label={{ value: "Power (kW)", angle: -90, position: "insideLeft" }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "6px",
          }}
        />
        <Area
          type="monotone"
          dataKey="power"
          stroke="hsl(var(--primary))"
          fill="hsl(var(--primary))"
          fillOpacity={0.3}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export default function OperatorDashboard() {
  const { data: dashboard, isLoading, error } = useQuery({
    queryKey: ["operator-dashboard"],
    queryFn: operatorApi.getDashboard,
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-12 h-12 mx-auto text-destructive mb-4" />
        <h2 className="text-2xl font-bold mb-2">Error Loading Dashboard</h2>
        <p className="text-muted-foreground">{error.message}</p>
      </div>
    );
  }

  const stations = dashboard?.stations || [];
  const queuedSessions = dashboard?.queued_sessions_list || [];
  const totalActiveSessions = stations.reduce((sum, s) => sum + (s.active_sessions || 0), 0);
  const totalPowerDraw = stations.reduce((sum, s) => sum + (s.current_power_draw || 0), 0);
  const averageUtilization =
    stations.length > 0
      ? stations.reduce(
          (sum, s) => sum + ((s.total_ports - s.available_ports) / s.total_ports) * 100,
          0
        ) / stations.length
      : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Station Operator Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Monitor and manage your charging stations
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Stations</CardDescription>
            <CardTitle className="text-3xl flex items-center gap-2">
              <Server className="w-6 h-6 text-primary" />
              {stations.length}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Active Sessions</CardDescription>
            <CardTitle className="text-3xl flex items-center gap-2">
              <Users className="w-6 h-6 text-primary" />
              {totalActiveSessions}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Power Draw</CardDescription>
            <CardTitle className="text-3xl flex items-center gap-2">
              <Zap className="w-6 h-6 text-primary" />
              {totalPowerDraw.toFixed(0)} kW
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Avg Utilization</CardDescription>
            <CardTitle className="text-3xl flex items-center gap-2">
              <TrendingUp className="w-6 h-6 text-primary" />
              {averageUtilization.toFixed(0)}%
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div>
        <h2 className="text-2xl font-bold mb-4">Station Fleet</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {stations.map((station) => (
            <StationCard key={station.id} station={station} />
          ))}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Live Queue</CardTitle>
          <CardDescription>Sessions waiting to charge</CardDescription>
        </CardHeader>
        <CardContent>
          <QueueTable sessions={queuedSessions} />
        </CardContent>
      </Card>

      {dashboard?.power_consumption_history && (
        <Card>
          <CardHeader>
            <CardTitle>Fleet Power Consumption</CardTitle>
            <CardDescription>Real-time power draw across all stations</CardDescription>
          </CardHeader>
          <CardContent>
            <PowerConsumptionChart data={dashboard.power_consumption_history} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
