import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gridOperatorApi } from "../../lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Label } from "../../components/ui/Label";
import { Badge } from "../../components/ui/Badge";
import {
  Activity,
  Sun,
  Wind,
  Leaf,
  DollarSign,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Zap,
} from "lucide-react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

function GridDemandChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>No grid demand data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={(value) => new Date(value).getHours() + ":00"}
          className="text-xs"
        />
        <YAxis label={{ value: "Power (MW)", angle: -90, position: "insideLeft" }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "6px",
          }}
          labelFormatter={(value) => new Date(value).toLocaleString()}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="base_load_mw"
          stroke="hsl(var(--primary))"
          name="Base Load"
          strokeWidth={2}
        />
        <Line
          type="monotone"
          dataKey="ev_load_mw"
          stroke="hsl(160, 84%, 39%)"
          name="EV Load"
          strokeWidth={2}
        />
        <Line
          type="monotone"
          dataKey="capacity_mw"
          stroke="hsl(var(--destructive))"
          name="Capacity"
          strokeWidth={2}
          strokeDasharray="5 5"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function RenewableGenerationChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Sun className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>No renewable generation data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={(value) => new Date(value).getHours() + ":00"}
          className="text-xs"
        />
        <YAxis label={{ value: "Generation (MW)", angle: -90, position: "insideLeft" }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "6px",
          }}
          labelFormatter={(value) => new Date(value).toLocaleString()}
        />
        <Legend />
        <Area
          type="monotone"
          dataKey="solar_mw"
          stackId="1"
          stroke="hsl(45, 93%, 47%)"
          fill="hsl(45, 93%, 47%)"
          fillOpacity={0.6}
          name="Solar"
        />
        <Area
          type="monotone"
          dataKey="wind_mw"
          stackId="1"
          stroke="hsl(200, 80%, 50%)"
          fill="hsl(200, 80%, 50%)"
          fillOpacity={0.6}
          name="Wind"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function CarbonPricingChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Leaf className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>No carbon and pricing data available</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={(value) => new Date(value).getHours() + ":00"}
          className="text-xs"
        />
        <YAxis yAxisId="left" label={{ value: "gCO₂/kWh", angle: -90, position: "insideLeft" }} />
        <YAxis
          yAxisId="right"
          orientation="right"
          label={{ value: "$/kWh", angle: 90, position: "insideRight" }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "6px",
          }}
          labelFormatter={(value) => new Date(value).toLocaleString()}
        />
        <Legend />
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="carbon_intensity_gco2_kwh"
          stroke="hsl(160, 84%, 39%)"
          name="Carbon Intensity"
          strokeWidth={2}
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="price_per_kwh"
          stroke="hsl(var(--primary))"
          name="Price"
          strokeWidth={2}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function GridEventModal({ onClose, onSubmit, isSubmitting, regions = [], initialRegion = "Maharashtra - Mumbai" }) {
  const [formData, setFormData] = useState({
    region: initialRegion,
    event_type: "GRID_STRESS",
    severity: "HIGH",
    message: "High grid load surge detected in regional feeder lines",
  });

  const handleEventTypeChange = (type) => {
    let msg = "High grid load surge detected in regional feeder lines";
    if (type === "CURTAILMENT") msg = "Renewable generation curtailment event active: excess solar/wind redirected";
    else if (type === "FREQUENCY_DROP") msg = "Grid frequency dropped below 49.85 Hz: rapid load regulation requested";
    else if (type === "PRICE_SPIKE") msg = "Surge in spot electricity tariff triggered by peak demand";
    else if (type === "EMERGENCY_REDUCTION") msg = "Emergency EV charging load reduction requested by Regional Load Dispatch Center";
    else if (type === "SUBSTATION_MAINTENANCE") msg = "Scheduled transformer maintenance active on regional substation";
    
    setFormData((prev) => ({ ...prev, event_type: type, message: msg }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <Card className="w-full max-w-md border-border shadow-2xl">
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-destructive/10 rounded-full">
              <AlertTriangle className="w-5 h-5 text-destructive" />
            </div>
            <div>
              <CardTitle>Trigger Grid Event</CardTitle>
              <CardDescription>Simulate a regional grid event or curtailment</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="region">Target Region</Label>
              <select
                id="region"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={formData.region}
                onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                required
              >
                {regions.map((r) => (
                  <option key={r.id || r.name} value={r.id || r.name}>
                    {r.name || r.id}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="event_type">Event Type</Label>
              <select
                id="event_type"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={formData.event_type}
                onChange={(e) => handleEventTypeChange(e.target.value)}
                required
              >
                <option value="GRID_STRESS">Grid Stress / Peak Demand Alert</option>
                <option value="CURTAILMENT">Renewable Energy Curtailment</option>
                <option value="FREQUENCY_DROP">Grid Frequency Drop (&lt;49.85 Hz)</option>
                <option value="PRICE_SPIKE">Dynamic Tariff Surge Spike</option>
                <option value="EMERGENCY_REDUCTION">Emergency EV Load Reduction</option>
                <option value="SUBSTATION_MAINTENANCE">Substation Maintenance</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="severity">Severity Level</Label>
              <select
                id="severity"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={formData.severity}
                onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
              >
                <option value="LOW">Low (Advisory)</option>
                <option value="MEDIUM">Medium (Moderate Curtailment)</option>
                <option value="HIGH">High (Mandatory EV Load Shift)</option>
                <option value="CRITICAL">Critical (Emergency Disconnect)</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="message">Broadcast Message</Label>
              <Input
                id="message"
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                placeholder="Enter event broadcast message"
                required
              />
            </div>

            <div className="flex gap-2 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isSubmitting}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button type="submit" variant="destructive" disabled={isSubmitting} className="flex-1">
                {isSubmitting ? "Broadcasting..." : "Trigger Event"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function GridOperatorDashboard() {
  const [showEventModal, setShowEventModal] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState("Maharashtra - Mumbai");
  const [eventAlert, setEventAlert] = useState(null);
  const queryClient = useQueryClient();

  const { data: regionsData } = useQuery({
    queryKey: ["grid-regions"],
    queryFn: gridOperatorApi.getRegions,
    staleTime: 60000,
  });

  const availableRegions = regionsData || [
    { id: "Maharashtra - Mumbai", name: "Maharashtra - Mumbai" },
    { id: "Karnataka - Bengaluru", name: "Karnataka - Bengaluru" },
    { id: "Delhi NCR - Central", name: "Delhi NCR - Central" },
    { id: "Gujarat - Ahmedabad", name: "Gujarat - Ahmedabad" },
    { id: "Telangana - Hyderabad", name: "Telangana - Hyderabad" },
    { id: "Tamil Nadu - Chennai", name: "Tamil Nadu - Chennai" },
    { id: "Andhra Pradesh - Visakhapatnam", name: "Andhra Pradesh - Visakhapatnam" },
    { id: "Andhra Pradesh - Vijayawada", name: "Andhra Pradesh - Vijayawada" },
    { id: "Andhra Pradesh - Tirupati", name: "Andhra Pradesh - Tirupati" },
  ];

  const { data: dashboard, isLoading: dashboardLoading } = useQuery({
    queryKey: ["grid-operator-dashboard", selectedRegion],
    queryFn: () => gridOperatorApi.getDashboard({ region: selectedRegion }),
    refetchInterval: 10000,
  });

  const { data: gridStatus } = useQuery({
    queryKey: ["grid-status", selectedRegion],
    queryFn: () => gridOperatorApi.getGridStatus({ region: selectedRegion }),
    refetchInterval: 10000,
  });

  const { data: renewableStatus } = useQuery({
    queryKey: ["renewable-status", selectedRegion],
    queryFn: () => gridOperatorApi.getRenewableStatus({ region: selectedRegion }),
    refetchInterval: 10000,
  });

  const { data: pricingData } = useQuery({
    queryKey: ["pricing-data", selectedRegion],
    queryFn: () => gridOperatorApi.getCurrentPricing({ region: selectedRegion }),
    refetchInterval: 10000,
  });

  const createEventMutation = useMutation({
    mutationFn: gridOperatorApi.createGridEvent,
    onSuccess: (data) => {
      setShowEventModal(false);
      setEventAlert({
        type: "success",
        message: data?.message || `Grid event triggered successfully in ${selectedRegion}!`,
      });
      queryClient.invalidateQueries(["grid-operator-dashboard"]);
      queryClient.invalidateQueries(["grid-status"]);
      queryClient.invalidateQueries(["renewable-status"]);
      queryClient.invalidateQueries(["pricing-data"]);
      queryClient.invalidateQueries(["grid-alerts"]);
      setTimeout(() => setEventAlert(null), 6000);
    },
    onError: (err) => {
      setEventAlert({
        type: "error",
        message: err?.detail?.message || err?.message || "Failed to trigger grid event. Please check backend connection.",
      });
      setTimeout(() => setEventAlert(null), 6000);
    },
  });

  if (dashboardLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  const latestGridPoint = Array.isArray(gridStatus) && gridStatus.length > 0 
    ? gridStatus[gridStatus.length - 1] 
    : gridStatus;
  const currentGridLoad = latestGridPoint?.base_load_mw !== undefined
    ? (latestGridPoint.base_load_mw + (latestGridPoint.ev_load_mw || 0))
    : (latestGridPoint?.demand_mw || 0);
  const gridCapacity = latestGridPoint?.capacity_mw || 2500;
  const utilizationPercent = gridCapacity > 0 ? (currentGridLoad / gridCapacity) * 100 : 0;
  
  const latestRenPoint = Array.isArray(renewableStatus) && renewableStatus.length > 0
    ? renewableStatus[renewableStatus.length - 1]
    : renewableStatus;
  const currentRenewable = latestRenPoint?.total_mw || ((latestRenPoint?.solar_mw || 0) + (latestRenPoint?.wind_mw || 0) + (latestRenPoint?.hydro_mw || 0));
  
  const latestPricePoint = Array.isArray(pricingData) && pricingData.length > 0
    ? pricingData[pricingData.length - 1]
    : pricingData;
  const currentCarbon = latestPricePoint?.carbon_intensity_gco2_kwh || latestPricePoint?.grid_carbon_intensity_gco2_per_kwh || 280;
  const currentPrice = latestPricePoint?.price_per_kwh || 0.22;

  return (
    <div className="space-y-6">
      {eventAlert && (
        <div className={`p-4 rounded-lg flex items-center justify-between transition-all ${
          eventAlert.type === "success" ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400" : "bg-destructive/10 border border-destructive/30 text-destructive"
        }`}>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-medium">{eventAlert.message}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setEventAlert(null)}>✕</Button>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Grid Operator Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Monitor regional grid health, renewable generation, and demand response
          </p>
        </div>
        <Button onClick={() => setShowEventModal(true)} variant="destructive">
          <AlertTriangle className="w-4 h-4 mr-2" />
          Trigger Grid Event
        </Button>
      </div>

      <div className="flex items-center gap-3 bg-card p-3 rounded-lg border">
        <span className="text-sm font-semibold text-muted-foreground">Active Grid Region:</span>
        <select
          className="h-10 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          value={selectedRegion}
          onChange={(e) => setSelectedRegion(e.target.value)}
        >
          {availableRegions.map((r) => (
            <option key={r.id || r.name} value={r.id || r.name}>
              {r.name || r.id}
            </option>
          ))}
        </select>
        <span className="text-xs text-muted-foreground ml-auto hidden sm:inline">
          Connected to Regional Load Dispatch Center (RLDC)
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Grid Load</CardDescription>
            <CardTitle className="text-3xl flex items-center gap-2">
              <Activity className="w-6 h-6 text-primary" />
              {currentGridLoad.toFixed(0)} MW
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 text-sm">
              {utilizationPercent > 90 ? (
                <TrendingUp className="w-4 h-4 text-destructive" />
              ) : (
                <TrendingDown className="w-4 h-4 text-emerald-500" />
              )}
              <span className="text-muted-foreground">
                {utilizationPercent.toFixed(1)}% of capacity
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Renewable Generation</CardDescription>
            <CardTitle className="text-3xl flex items-center gap-2">
              <Sun className="w-6 h-6 text-yellow-500" />
              {currentRenewable.toFixed(0)} MW
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Badge variant="success" className="text-xs">
                <Leaf className="w-3 h-3 mr-1" />
                Clean Energy
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Carbon Intensity</CardDescription>
            <CardTitle className="text-3xl flex items-center gap-2">
              <Leaf className="w-6 h-6 text-emerald-500" />
              {currentCarbon.toFixed(0)} g
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-muted-foreground">gCO₂/kWh</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Current Price</CardDescription>
            <CardTitle className="text-3xl flex items-center gap-2">
              <DollarSign className="w-6 h-6 text-primary" />
              ${currentPrice.toFixed(3)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-muted-foreground">per kWh</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Grid Demand vs Capacity</CardTitle>
          <CardDescription>24-hour regional demand and EV charging load</CardDescription>
        </CardHeader>
        <CardContent>
          <GridDemandChart data={gridStatus} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Renewable Generation</CardTitle>
          <CardDescription>Solar and wind energy production curves</CardDescription>
        </CardHeader>
        <CardContent>
          <RenewableGenerationChart data={renewableStatus} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Carbon Intensity & Dynamic Pricing</CardTitle>
          <CardDescription>24-hour emissions and tariff trends</CardDescription>
        </CardHeader>
        <CardContent>
          <CarbonPricingChart data={pricingData} />
        </CardContent>
      </Card>

      {showEventModal && (
        <GridEventModal
          onClose={() => setShowEventModal(false)}
          onSubmit={(data) => createEventMutation.mutate(data)}
          isSubmitting={createEventMutation.isPending}
          regions={availableRegions}
          initialRegion={selectedRegion}
        />
      )}
    </div>
  );
}
