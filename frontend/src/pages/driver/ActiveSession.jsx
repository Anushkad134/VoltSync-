import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import { sessionsApi } from "../../lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { StatusBadge, getStatusDescription } from "../../components/StatusBadge";
import { Badge } from "../../components/ui/Badge";
import {
  Battery,
  Clock,
  Zap,
  DollarSign,
  Leaf,
  Calendar,
  RefreshCw,
  XCircle,
  ArrowLeft,
  Sun,
  Wind,
  Activity,
  TrendingUp,
  AlertCircle,
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

function ChargingTimeline({ schedule }) {
  const actualSchedule = schedule?.data || schedule;
  const segments = actualSchedule?.schedule_segments || actualSchedule?.segments || [];
  if (!actualSchedule || segments.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Clock className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>No schedule available yet</p>
      </div>
    );
  }

  const chartData = segments.map((segment) => ({
    name: segment.start_time ? `${new Date(segment.start_time).getHours()}:${String(new Date(segment.start_time).getMinutes()).padStart(2, "0")}` : "00:00",
    power: segment.power_kw ?? segment.power_level_kw ?? 0,
    cost: segment.cost_estimate ?? segment.expected_cost_inr ?? 0,
    carbon: segment.carbon_gco2 ?? segment.expected_co2_g ?? 0,
    startTime: segment.start_time,
    endTime: segment.end_time,
  }));

  return (
    <div className="space-y-4">
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey="name" className="text-xs" />
          <YAxis label={{ value: "Power (kW)", angle: -90, position: "insideLeft" }} />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
            }}
            labelStyle={{ color: "hsl(var(--foreground))" }}
          />
          <Bar dataKey="power" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.carbon < 100 ? "hsl(160, 84%, 39%)" : "hsl(var(--primary))"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {segments.map((segment, idx) => {
          const power = segment.power_kw ?? segment.power_level_kw ?? 0;
          const cost = segment.cost_estimate ?? segment.expected_cost_inr ?? 0;
          const carbon = segment.carbon_gco2 ?? segment.expected_co2_g ?? 0;
          return (
            <div
              key={idx}
              className="p-3 border rounded-lg space-y-2 hover:bg-accent transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">
                  {segment.start_time ? new Date(segment.start_time).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  }) : "TBD"}
                  {" - "}
                  {segment.end_time ? new Date(segment.end_time).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  }) : "TBD"}
                </span>
                <Badge variant={carbon < 100 ? "success" : "secondary"} className="text-xs">
                  {power} kW
                </Badge>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <DollarSign className="w-3 h-3" />
                  ₹{Number(cost).toFixed(2)}
                </div>
                <div className="flex items-center gap-1">
                  <Leaf className="w-3 h-3" />
                  {carbon}g CO₂
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AgentInsights({ agentOutputs }) {
  if (!agentOutputs || Object.keys(agentOutputs).length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>No agent insights available yet</p>
      </div>
    );
  }

  const agents = [
    {
      key: "driver_agent",
      altKey: "driver",
      title: "Driver Agent",
      icon: Zap,
      color: "text-yellow-500",
      description: "Driver constraints, urgency & energy requirements",
    },
    {
      key: "renewable_agent",
      altKey: "renewable",
      title: "Renewable Agent",
      icon: Sun,
      color: "text-emerald-500",
      description: "Solar & wind availability forecast",
    },
    {
      key: "grid_agent",
      altKey: "grid",
      title: "Grid Agent",
      icon: Activity,
      color: "text-blue-500",
      description: "Grid congestion & substation stress analysis",
    },
    {
      key: "cost_carbon_agent",
      altKey: "cost_carbon",
      title: "Cost & Carbon Agent",
      icon: TrendingUp,
      color: "text-cyan-500",
      description: "Price & carbon emissions trade-off optimization",
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {agents.map((agent) => {
        const output = agentOutputs[agent.key] || agentOutputs[agent.altKey];
        if (!output) return null;

        const Icon = agent.icon;
        return (
          <Card key={agent.key} className="border-border/60">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Icon className={`w-5 h-5 ${agent.color}`} />
                <CardTitle className="text-lg">{agent.title}</CardTitle>
              </div>
              <CardDescription className="text-xs">{agent.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                {typeof output === "string" ? (
                  <p className="text-muted-foreground">{output}</p>
                ) : (
                  <div className="space-y-1.5">
                    {Object.entries(output).map(([key, value]) => {
                      if (key === "session_id" || key === "candidate_windows" || key === "green_windows") return null;
                      let displayVal = value;
                      if (typeof value === "boolean") displayVal = value ? "Yes" : "No";
                      else if (Array.isArray(value)) displayVal = value.length ? `${value.length} window(s)` : "None";
                      else if (typeof value === "object" && value !== null) displayVal = JSON.stringify(value);
                      
                      return (
                        <div key={key} className="flex justify-between items-center text-xs">
                          <span className="text-muted-foreground capitalize">
                            {key.replace(/_/g, " ")}:
                          </span>
                          <span className="font-medium text-right max-w-[60%] truncate" title={String(displayVal)}>
                            {String(displayVal)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

export default function ActiveSession() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => sessionsApi.getById(sessionId),
    refetchInterval: 5000,
  });

  const { data: schedule, isLoading: scheduleLoading } = useQuery({
    queryKey: ["session-schedule", sessionId],
    queryFn: () => sessionsApi.getSchedule(sessionId),
    enabled: !!session,
    refetchInterval: 10000,
  });

  const recalculateMutation = useMutation({
    mutationFn: () => sessionsApi.recalculate(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries(["session", sessionId]);
      queryClient.invalidateQueries(["session-schedule", sessionId]);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => sessionsApi.cancel(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries(["session", sessionId]);
      navigate("/driver");
    },
  });

  if (sessionLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 mx-auto text-destructive mb-4" />
        <h2 className="text-2xl font-bold mb-2">Session Not Found</h2>
        <Button onClick={() => navigate("/driver")}>Back to Dashboard</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/driver")}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Charging Session</h1>
            <p className="text-muted-foreground">Session ID: {session.id || session.session_id}</p>
          </div>
        </div>
        <StatusBadge status={session.status || "Queued"} />
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Current SOC</CardDescription>
            <CardTitle className="text-3xl flex items-center gap-2">
              <Battery className="w-6 h-6 text-primary" />
              {session.current_soc ?? session.initial_soc_pct ?? 0}%
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Target SOC</CardDescription>
            <CardTitle className="text-3xl flex items-center gap-2">
              <Zap className="w-6 h-6 text-primary" />
              {session.target_soc ?? session.target_soc_pct ?? 0}%
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Preference</CardDescription>
            <CardTitle className="text-xl">{session.preference || "Greenest"}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Flexibility</CardDescription>
            <CardTitle className="text-xl">{session.flexibility || "Medium"}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Session Details</CardTitle>
              <CardDescription>{getStatusDescription(session.status || "Queued")}</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => recalculateMutation.mutate()}
                disabled={recalculateMutation.isPending || session.status === "COMPLETED"}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Recalculate
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  if (confirm("Are you sure you want to cancel this session?")) {
                    cancelMutation.mutate();
                  }
                }}
                disabled={cancelMutation.isPending || session.status === "COMPLETED"}
              >
                <XCircle className="w-4 h-4 mr-2" />
                Cancel
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-muted-foreground">Station</div>
              <div className="font-medium">{session.station_id}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Port</div>
              <div className="font-medium">{session.port_id || "PORT_A"}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Battery Capacity</div>
              <div className="font-medium">{session.battery_capacity_kwh} kWh</div>
            </div>
            <div>
              <div className="text-muted-foreground">Max Power</div>
              <div className="font-medium">{session.max_charge_power_kw ?? session.max_charging_power_kw ?? 0} kW</div>
            </div>
            {session.ready_by && (
              <div>
                <div className="text-muted-foreground">Ready By</div>
                <div className="font-medium flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(session.ready_by).toLocaleString()}
                </div>
              </div>
            )}
            <div>
              <div className="text-muted-foreground">Created</div>
              <div className="font-medium flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {new Date(session.created_at).toLocaleString()}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Smart Charging Schedule</CardTitle>
          <CardDescription>
            AI-optimized charging timeline based on your preferences
          </CardDescription>
        </CardHeader>
        <CardContent>
          {scheduleLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : (
            <ChargingTimeline schedule={schedule} />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI Agent Insights</CardTitle>
          <CardDescription>
            Recommendations from our multi-agent orchestration system
          </CardDescription>
        </CardHeader>
        <CardContent>
          {scheduleLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : (
            <AgentInsights agentOutputs={schedule?.data?.agent_outputs || schedule?.agent_outputs} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
