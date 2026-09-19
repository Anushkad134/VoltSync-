import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { stationsApi, sessionsApi } from "../../lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Label } from "../../components/ui/Label";
import { Select } from "../../components/ui/Select";
import { Badge } from "../../components/ui/Badge";
import { useNavigate } from "react-router-dom";
import { MapPin, Zap, Battery, Leaf, DollarSign, Clock, AlertCircle } from "lucide-react";

function SessionCreateModal({ station, onClose, onSuccess }) {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    station_id: station.station_id || station.id,
    port_id: `PORT_A`,
    current_soc: 20,
    target_soc: 80,
    battery_capacity_kwh: 60,
    max_charge_power_kw: 150,
    ready_by: "",
    preference: "Greenest",
    flexibility: "Medium",
    phone_number: "",
    whatsapp_opt_in: true,
  });

  const createMutation = useMutation({
    mutationFn: sessionsApi.create,
    onSuccess: (data) => {
      onSuccess();
      const sessionId = data?.id || data?.session_id;
      navigate(`/driver/session/${sessionId}`);
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const submitData = {
      ...formData,
      station_id: station.station_id || station.id,
      current_soc: Number(formData.current_soc),
      target_soc: Number(formData.target_soc),
      battery_capacity_kwh: Number(formData.battery_capacity_kwh),
      max_charge_power_kw: Number(formData.max_charge_power_kw),
      ready_by: formData.ready_by ? new Date(formData.ready_by).toISOString() : new Date(Date.now() + 3600000).toISOString(),
    };
    createMutation.mutate(submitData);
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader>
          <CardTitle>Create Charging Session</CardTitle>
          <CardDescription>{station.name} - {station.location}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="current_soc">Current SOC (%)</Label>
                <Input
                  id="current_soc"
                  name="current_soc"
                  type="number"
                  min="0"
                  max="100"
                  value={formData.current_soc}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="target_soc">Target SOC (%)</Label>
                <Input
                  id="target_soc"
                  name="target_soc"
                  type="number"
                  min="0"
                  max="100"
                  value={formData.target_soc}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="battery_capacity_kwh">Battery Capacity (kWh)</Label>
                <Input
                  id="battery_capacity_kwh"
                  name="battery_capacity_kwh"
                  type="number"
                  step="0.1"
                  value={formData.battery_capacity_kwh}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="max_charge_power_kw">Max Charge Power (kW)</Label>
                <Input
                  id="max_charge_power_kw"
                  name="max_charge_power_kw"
                  type="number"
                  step="0.1"
                  value={formData.max_charge_power_kw}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="ready_by">Ready By (Optional)</Label>
              <Input
                id="ready_by"
                name="ready_by"
                type="datetime-local"
                value={formData.ready_by}
                onChange={handleChange}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="preference">Charging Preference</Label>
                <Select
                  id="preference"
                  name="preference"
                  value={formData.preference}
                  onChange={handleChange}
                >
                  <option value="Fastest">Fastest</option>
                  <option value="Cheapest">Cheapest</option>
                  <option value="Greenest">Greenest</option>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="flexibility">Flexibility</Label>
                <Select
                  id="flexibility"
                  name="flexibility"
                  value={formData.flexibility}
                  onChange={handleChange}
                >
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone_number">Phone Number (E.164 format, e.g., +1234567890)</Label>
              <Input
                id="phone_number"
                name="phone_number"
                type="tel"
                placeholder="+1234567890"
                value={formData.phone_number}
                onChange={handleChange}
              />
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="whatsapp_opt_in"
                name="whatsapp_opt_in"
                checked={formData.whatsapp_opt_in}
                onChange={handleChange}
                className="rounded border-gray-300"
              />
              <Label htmlFor="whatsapp_opt_in" className="cursor-pointer">
                Receive WhatsApp notifications
              </Label>
            </div>

            {createMutation.isError && (
              <div className="flex items-center gap-2 p-3 bg-destructive/10 border border-destructive rounded-md text-destructive text-sm">
                <AlertCircle className="w-4 h-4" />
                {createMutation.error.message}
              </div>
            )}

            <div className="flex gap-2 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={createMutation.isPending}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending} className="flex-1">
                {createMutation.isPending ? "Creating..." : "Create Session"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function StationDiscovery() {
  const [selectedStation, setSelectedStation] = useState(null);
  const [regionFilter, setRegionFilter] = useState("");

  const { data: stations, isLoading, refetch } = useQuery({
    queryKey: ["stations", regionFilter],
    queryFn: () => stationsApi.getAll({ region: regionFilter, status: "AVAILABLE" }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Find Charging Stations</h1>
        <p className="text-muted-foreground mt-1">
          Discover available charging stations and start a session
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <Select
          value={regionFilter}
          onChange={(e) => setRegionFilter(e.target.value)}
          className="max-w-sm"
        >
          <option value="">All Regions</option>
          <option value="Maharashtra - Mumbai">Maharashtra - Mumbai</option>
          <option value="Delhi - NCR">Delhi - NCR</option>
          <option value="Karnataka - Bengaluru">Karnataka - Bengaluru</option>
          <option value="Gujarat - Ahmedabad">Gujarat - Ahmedabad</option>
          <option value="Telangana - Hyderabad">Telangana - Hyderabad</option>
          <option value="Tamil Nadu - Chennai">Tamil Nadu - Chennai</option>
        </Select>
        <Button 
          variant="secondary" 
          onClick={() => {
            setRegionFilter("Maharashtra - Mumbai");
          }}
        >
          <MapPin className="w-4 h-4 mr-2" />
          Use My Location
        </Button>
        <Button variant="outline" onClick={() => refetch()}>
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : stations && stations.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {stations.map((station) => (
            <Card key={station.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{station.name}</CardTitle>
                    <CardDescription className="flex items-center gap-1 mt-1">
                      <MapPin className="w-3 h-3" />
                      {station.location}
                    </CardDescription>
                  </div>
                  <Badge variant={station.status === "AVAILABLE" ? "success" : "secondary"}>
                    {station.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-primary" />
                    <span>{station.total_ports} ports</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Battery className="w-4 h-4 text-primary" />
                    <span>{station.available_ports} available</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-primary" />
                    <span>₹{station.current_tariff?.toFixed(2)}/kWh</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Leaf className="w-4 h-4 text-emerald-500" />
                    <span>{station.green_score || 0}% green</span>
                  </div>
                </div>

                <div className="text-xs text-muted-foreground">
                  <div>Max Power: {station.max_power_kw} kW</div>
                  <div>Chargers: {station.charger_types?.join(", ") || "CCS, Type 2"}</div>
                </div>

                <Button
                  onClick={() => setSelectedStation(station)}
                  disabled={station.available_ports === 0}
                  className="w-full"
                >
                  <Clock className="w-4 h-4 mr-2" />
                  Start Session
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-12">
            <MapPin className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No stations found</h3>
            <p className="text-muted-foreground">
              Try adjusting your filters or check back later
            </p>
          </CardContent>
        </Card>
      )}

      {selectedStation && (
        <SessionCreateModal
          station={selectedStation}
          onClose={() => setSelectedStation(null)}
          onSuccess={() => {
            setSelectedStation(null);
            refetch();
          }}
        />
      )}
    </div>
  );
}
