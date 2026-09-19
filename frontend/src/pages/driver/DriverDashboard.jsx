import { useQuery } from "@tanstack/react-query";
import { sessionsApi } from "../../lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { StatusBadge } from "../../components/StatusBadge";
import { Link, useNavigate } from "react-router-dom";
import { MapPin, Zap, Clock, Calendar } from "lucide-react";

export default function DriverDashboard() {
  const navigate = useNavigate();
  const { data: sessions, isLoading } = useQuery({
    queryKey: ["my-sessions"],
    queryFn: sessionsApi.getMySessions,
    refetchInterval: 10000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Driver Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Manage your charging sessions and find stations
          </p>
        </div>
        <Button size="lg" onClick={() => navigate("/driver/stations")}>
          <MapPin className="w-4 h-4 mr-2" />
          Find Stations
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Active Sessions</CardDescription>
            <CardTitle className="text-3xl">
              {sessions?.filter((s) => s.status === "CHARGING" || s.status === "SCHEDULED").length || 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Sessions</CardDescription>
            <CardTitle className="text-3xl">{sessions?.length || 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Completed</CardDescription>
            <CardTitle className="text-3xl">
              {sessions?.filter((s) => s.status === "COMPLETED").length || 0}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Charging Sessions</CardTitle>
          <CardDescription>View and manage your charging sessions</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : sessions && sessions.length > 0 ? (
            <div className="space-y-4">
              {sessions.map((session) => (
                <Link
                  key={session.id}
                  to={`/driver/session/${session.id}`}
                  className="block"
                >
                  <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent transition-colors">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <Zap className="w-4 h-4 text-primary" />
                        <span className="font-medium">{session.station_name || `Station ${session.station_id}`}</span>
                        <StatusBadge status={session.status} />
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {session.current_soc}% → {session.target_soc}%
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {new Date(session.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm">
                      View Details →
                    </Button>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <Zap className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No charging sessions yet</h3>
              <p className="text-muted-foreground mb-4">
                Start by finding a charging station near you
              </p>
              <Button onClick={() => navigate("/driver/stations")}>
                <MapPin className="w-4 h-4 mr-2" />
                Find Stations
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
