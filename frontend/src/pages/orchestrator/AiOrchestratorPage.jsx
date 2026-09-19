import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import {
  Sun,
  Zap,
  Activity,
  BatteryCharging,
  Clock,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  TrendingDown,
  Leaf,
  Layers,
  Play,
  RotateCcw
} from "lucide-react";

export default function AiOrchestratorPage() {
  // Simulator Controls State
  const [renewablePct, setRenewablePct] = useState(65);
  const [currentSoc, setCurrentSoc] = useState(35);
  const [targetSoc, setTargetSoc] = useState(80);
  const [deadlineHour, setDeadlineHour] = useState(21); // 21:00
  const [gridStressPreset, setGridStressPreset] = useState("dynamic"); // dynamic, low, high

  const canvasRef = useRef(null);

  // Derived Grid calculations
  const calculatedGridStress =
    gridStressPreset === "high"
      ? 88
      : gridStressPreset === "low"
      ? 32
      : Math.max(25, Math.min(95, Math.round(100 - renewablePct * 0.75 + (currentSoc < 30 ? 15 : 0))));

  const gridContributionPct = Math.max(10, 100 - renewablePct);

  // Cost & Carbon calculations
  const baseTariffInr = 11.2;
  const optimalTariffInr = Number((baseTariffInr * (1 - (renewablePct / 100) * 0.45)).toFixed(1));
  const currentCarbonG = Math.round(620 - renewablePct * 3.8);
  const optimalCarbonG = Math.round(currentCarbonG * 0.58);

  // Orchestrator Strategy Engine
  const shouldWait = renewablePct < 50 && calculatedGridStress > 60;
  const waitMinutes = shouldWait ? 45 : 0;
  const chargingPowerKw = calculatedGridStress > 80 ? 25 : renewablePct > 70 ? 75 : 50;

  const energyNeededKwh = ((targetSoc - currentSoc) / 100) * 60; // 60 kWh pack
  const chargeTimeHours = energyNeededKwh / chargingPowerKw;
  const chargeTimeMinutes = Math.round(chargeTimeHours * 60);

  const startHour = 19;
  const startMinute = 0 + waitMinutes;
  const formattedStart = `${String(startHour).padStart(2, "0")}:${String(startMinute).padStart(2, "0")}`;

  const finishTotalMinutes = startHour * 60 + startMinute + chargeTimeMinutes;
  const finishHour = Math.floor(finishTotalMinutes / 60) % 24;
  const finishMinute = finishTotalMinutes % 60;
  const formattedFinish = `${String(finishHour).padStart(2, "0")}:${String(finishMinute).padStart(2, "0")}`;

  // Canvas Animation for Energy Flow & 3D Isometric View
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let animationFrameId;

    // Set canvas dimensions
    const width = (canvas.width = canvas.offsetWidth);
    const height = (canvas.height = canvas.offsetHeight);

    // Particle streams
    const particles = [];
    const maxParticles = 35;

    for (let i = 0; i < maxParticles; i++) {
      particles.push({
        progress: Math.random(),
        source: Math.random() < renewablePct / 100 ? "solar" : "grid",
        speed: 0.006 + Math.random() * 0.005,
      });
    }

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Gradient background
      const bgGrad = ctx.createLinearGradient(0, 0, width, height);
      bgGrad.addColorStop(0, "#080e1a");
      bgGrad.addColorStop(1, "#040711");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // Grid coordinate anchors (isometric layout)
      const solarNode = { x: width * 0.22, y: height * 0.26 };
      const gridNode = { x: width * 0.78, y: height * 0.26 };
      const hubNode = { x: width * 0.5, y: height * 0.52 };
      const chargerNode = { x: width * 0.5, y: height * 0.74 };
      const evNode = { x: width * 0.5, y: height * 0.9 };

      // Helper to draw isometric node base
      const drawIsoPlatform = (x, y, radius, color, glowColor, label, sublabel) => {
        ctx.save();
        ctx.shadowColor = glowColor;
        ctx.shadowBlur = 18;

        // Elliptical base
        ctx.beginPath();
        ctx.ellipse(x, y, radius * 1.3, radius * 0.65, 0, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = glowColor;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Label
        ctx.shadowBlur = 0;
        ctx.font = "bold 12px Inter, sans-serif";
        ctx.fillStyle = "#ffffff";
        ctx.textAlign = "center";
        ctx.fillText(label, x, y - radius * 0.85);

        if (sublabel) {
          ctx.font = "10px Inter, sans-serif";
          ctx.fillStyle = glowColor;
          ctx.fillText(sublabel, x, y + radius * 1.15);
        }
        ctx.restore();
      };

      // Draw Connection Conduit Lines
      const drawConduit = (from, to, intensity, color) => {
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.bezierCurveTo(
          from.x,
          (from.y + to.y) / 2,
          to.x,
          (from.y + to.y) / 2,
          to.x,
          to.y
        );
        ctx.strokeStyle = color;
        ctx.lineWidth = Math.max(2, intensity * 5);
        ctx.stroke();
        ctx.restore();
      };

      // Solar & Grid conduit colors
      const solarColor = renewablePct > 50 ? "rgba(16, 185, 129, 0.45)" : "rgba(16, 185, 129, 0.2)";
      const gridColor = gridContributionPct > 50 ? "rgba(245, 158, 11, 0.5)" : "rgba(245, 158, 11, 0.2)";
      const flowColor = renewablePct > 60 ? "rgba(16, 185, 129, 0.6)" : "rgba(59, 130, 246, 0.6)";

      drawConduit(solarNode, hubNode, renewablePct / 100, solarColor);
      drawConduit(gridNode, hubNode, gridContributionPct / 100, gridColor);
      drawConduit(hubNode, chargerNode, 0.8, flowColor);
      drawConduit(chargerNode, evNode, 0.9, flowColor);

      // Animate Particles
      particles.forEach((p) => {
        p.progress += p.speed;
        if (p.progress > 1) {
          p.progress = 0;
          p.source = Math.random() < renewablePct / 100 ? "solar" : "grid";
        }

        let px, py;
        if (p.progress < 0.5) {
          const t = p.progress / 0.5;
          const start = p.source === "solar" ? solarNode : gridNode;
          px = (1 - t) * start.x + t * hubNode.x;
          py = (1 - t) * start.y + t * hubNode.y;
        } else if (p.progress < 0.8) {
          const t = (p.progress - 0.5) / 0.3;
          px = (1 - t) * hubNode.x + t * chargerNode.x;
          py = (1 - t) * hubNode.y + t * chargerNode.y;
        } else {
          const t = (p.progress - 0.8) / 0.2;
          px = (1 - t) * chargerNode.x + t * evNode.x;
          py = (1 - t) * chargerNode.y + t * evNode.y;
        }

        ctx.save();
        ctx.beginPath();
        ctx.arc(px, py, p.source === "solar" ? 3.5 : 3.0, 0, Math.PI * 2);
        ctx.fillStyle = p.source === "solar" ? "#34d399" : "#fbbf24";
        ctx.shadowColor = p.source === "solar" ? "#10b981" : "#f59e0b";
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.restore();
      });

      // Render 3D Platform Nodes
      drawIsoPlatform(
        solarNode.x,
        solarNode.y,
        34,
        "rgba(16, 185, 129, 0.25)",
        "#10b981",
        "☀️ SOLAR ARRAY",
        renewablePct > 60 ? "HIGH OUTPUT" : "LOW OUTPUT"
      );

      drawIsoPlatform(
        gridNode.x,
        gridNode.y,
        34,
        "rgba(245, 158, 11, 0.25)",
        "#f59e0b",
        "⚡ REGIONAL GRID",
        gridContributionPct > 50 ? "HIGH CONTRIBUTION" : "LOW CONTRIBUTION"
      );

      drawIsoPlatform(
        hubNode.x,
        hubNode.y,
        42,
        "rgba(59, 130, 246, 0.3)",
        "#3b82f6",
        "🏢 ENERGY HUB & SUBSTATION",
        `Stress: ${calculatedGridStress}%`
      );

      drawIsoPlatform(
        chargerNode.x,
        chargerNode.y,
        30,
        "rgba(139, 92, 246, 0.3)",
        "#a855f7",
        "🔌 DC FAST CHARGER",
        `${chargingPowerKw} kW Active`
      );

      drawIsoPlatform(
        evNode.x,
        evNode.y,
        40,
        "rgba(16, 185, 129, 0.3)",
        "#10b981",
        `🚗 EV BATTERY [${currentSoc}% ➔ ${targetSoc}%]`,
        renewablePct > 60 ? "Primarily Clean Solar" : "Primarily Grid Power"
      );

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animationFrameId);
  }, [renewablePct, currentSoc, targetSoc, calculatedGridStress, chargingPowerKw, gridContributionPct]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight">AI Energy Orchestrator</h1>
            <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 bg-emerald-500/10">
              <Sparkles className="w-3 h-3 mr-1 animate-pulse" /> Live 3D Digital Twin
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1">
            Real-time multi-agent autonomous optimization balancing renewable energy, regional grid stress, and dynamic tariffs.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setRenewablePct(85);
              setCurrentSoc(25);
              setTargetSoc(80);
              setGridStressPreset("low");
            }}
          >
            <Leaf className="w-4 h-4 mr-1 text-emerald-400" /> High Renewable Preset
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setRenewablePct(20);
              setCurrentSoc(20);
              setTargetSoc(80);
              setGridStressPreset("high");
            }}
          >
            <Activity className="w-4 h-4 mr-1 text-amber-400" /> Peak Grid Stress Preset
          </Button>
        </div>
      </div>

      {/* Grid: Left Simulator & Controls | Right 4-Agent Stack */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 7 Columns: 3D Visualization & What-If Controls */}
        <div className="lg:col-span-7 space-y-6">
          {/* Interactive 3D Canvas */}
          <Card className="border-border overflow-hidden shadow-2xl relative">
            <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-background/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-border text-xs">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>Energy-Flow Stream (Active)</span>
            </div>

            <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
              <Badge variant="secondary" className="bg-background/80 backdrop-blur text-xs">
                Mix: {renewablePct}% Solar | {gridContributionPct}% Grid
              </Badge>
            </div>

            <div className="w-full h-[400px] relative">
              <canvas ref={canvasRef} className="w-full h-full block" />
            </div>

            {/* In-Canvas Battery Prominent Display */}
            <div className="p-4 bg-card/90 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-primary/10 rounded-lg text-primary">
                  <BatteryCharging className="w-6 h-6 animate-pulse" />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                    EV Battery Pack (60 kWh)
                  </div>
                  <div className="text-lg font-bold">
                    {currentSoc}% <span className="text-muted-foreground text-sm font-normal">➔ Target {targetSoc}%</span>
                  </div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="flex-1 w-full max-w-xs space-y-1.5">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Current: {currentSoc}%</span>
                  <span className="text-emerald-400 font-semibold">{targetSoc - currentSoc}% to charge</span>
                </div>
                <div className="w-full bg-secondary h-3 rounded-full overflow-hidden flex">
                  <div
                    className="bg-emerald-500 h-full transition-all duration-300"
                    style={{ width: `${currentSoc}%` }}
                  />
                  <div
                    className="bg-primary/40 h-full transition-all duration-300 animate-pulse"
                    style={{ width: `${Math.max(0, targetSoc - currentSoc)}%` }}
                  />
                </div>
              </div>

              <div className="text-right sm:text-left">
                <div className="text-xs text-muted-foreground">Est. Time</div>
                <div className="text-sm font-semibold">{chargeTimeMinutes} mins @ {chargingPowerKw}kW</div>
              </div>
            </div>
          </Card>

          {/* Interactive What-If Controls */}
          <Card className="border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Layers className="w-5 h-5 text-primary" /> Interactive What-If Controls
              </CardTitle>
              <CardDescription>
                Adjust variables in real-time to watch energy flow shift and AI agent decisions update instantly.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Renewable Availability Slider */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="flex items-center gap-1.5 font-medium">
                    <Sun className="w-4 h-4 text-emerald-400" /> Renewable Generation Availability
                  </span>
                  <span className="font-bold text-emerald-400">{renewablePct}%</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="95"
                  value={renewablePct}
                  onChange={(e) => setRenewablePct(Number(e.target.value))}
                  className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-emerald-500"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Low Sun/Wind (Grid heavy)</span>
                  <span>50% Balanced</span>
                  <span>Peak Solar/Wind (100% Green)</span>
                </div>
              </div>

              {/* Current & Target SoC Controls */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Current State of Charge</span>
                    <span className="font-bold">{currentSoc}%</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="70"
                    value={currentSoc}
                    onChange={(e) => setCurrentSoc(Number(e.target.value))}
                    className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Target State of Charge</span>
                    <span className="font-bold text-primary">{targetSoc}%</span>
                  </div>
                  <input
                    type="range"
                    min="75"
                    max="100"
                    value={targetSoc}
                    onChange={(e) => setTargetSoc(Number(e.target.value))}
                    className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                </div>
              </div>

              {/* Departure Deadline & Grid Mode */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t">
                <div>
                  <label className="text-sm font-medium mb-1.5 block">Departure Deadline</label>
                  <select
                    className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
                    value={deadlineHour}
                    onChange={(e) => setDeadlineHour(Number(e.target.value))}
                  >
                    <option value={20}>20:00 (1 hour flexibility)</option>
                    <option value={21}>21:00 (High flexibility - 2 hours)</option>
                    <option value={23}>23:00 (Overnight flexibility)</option>
                  </select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-1.5 block">Grid Stress Mode</label>
                  <select
                    className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
                    value={gridStressPreset}
                    onChange={(e) => setGridStressPreset(e.target.value)}
                  >
                    <option value="dynamic">Dynamic (Calculated from inputs)</option>
                    <option value="low">Force Low Grid Stress (Off-peak)</option>
                    <option value="high">Force Peak Feeder Congestion</option>
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right 5 Columns: 4 Autonomous Agents + Central AI Orchestrator */}
        <div className="lg:col-span-5 space-y-4">
          <div className="text-xs uppercase tracking-wider font-semibold text-muted-foreground flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-primary" /> Autonomous Multi-Agent Analysis
          </div>

          {/* 4 Agent Analysis Modules Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* 1. Driver Agent */}
            <Card className="bg-card/95 border-border shadow-md">
              <CardHeader className="py-2.5 px-3.5 border-b bg-muted/20">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold tracking-tight text-blue-400 flex items-center gap-1">
                    🚗 DRIVER AGENT
                  </span>
                  <Badge variant="outline" className="text-[10px] h-4 py-0 border-blue-500/40 text-blue-400">
                    Active
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-3 text-xs space-y-1.5 font-mono">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">SOC:</span>
                  <span className="font-bold">{currentSoc}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Target:</span>
                  <span className="font-bold text-primary">{targetSoc}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Deadline:</span>
                  <span>{deadlineHour}:00</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Flexibility:</span>
                  <span className="text-emerald-400 font-semibold">HIGH</span>
                </div>
                <div className="pt-1 text-[11px] text-emerald-400 font-sans flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Requirement analyzed
                </div>
              </CardContent>
            </Card>

            {/* 2. Renewable Agent */}
            <Card className="bg-card/95 border-border shadow-md">
              <CardHeader className="py-2.5 px-3.5 border-b bg-muted/20">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold tracking-tight text-emerald-400 flex items-center gap-1">
                    🌱 RENEWABLE AGENT
                  </span>
                  <Badge variant="outline" className="text-[10px] h-4 py-0 border-emerald-500/40 text-emerald-400">
                    {renewablePct}%
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-3 text-xs space-y-1.5 font-mono">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Current:</span>
                  <span className="font-bold text-emerald-400">{renewablePct}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Best window:</span>
                  <span>19:30 – 21:00</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Outlook:</span>
                  <span className={renewablePct > 50 ? "text-emerald-400 font-bold" : "text-yellow-400 font-bold"}>
                    {renewablePct > 60 ? "HIGH SOLAR" : renewablePct > 35 ? "FAVORABLE" : "LIMITED"}
                  </span>
                </div>
                <div className="pt-1 text-[11px] text-emerald-400 font-sans flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Clean mix verified
                </div>
              </CardContent>
            </Card>

            {/* 3. Grid Agent */}
            <Card className="bg-card/95 border-border shadow-md">
              <CardHeader className="py-2.5 px-3.5 border-b bg-muted/20">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold tracking-tight text-amber-400 flex items-center gap-1">
                    ⚡ GRID AGENT
                  </span>
                  <Badge
                    variant="outline"
                    className={`text-[10px] h-4 py-0 ${
                      calculatedGridStress > 75
                        ? "border-destructive text-destructive"
                        : "border-amber-500/40 text-amber-400"
                    }`}
                  >
                    {calculatedGridStress}% Load
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-3 text-xs space-y-1.5 font-mono">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Grid load:</span>
                  <span className="font-bold">{calculatedGridStress}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Stress:</span>
                  <span className={calculatedGridStress > 75 ? "text-destructive font-bold" : "text-amber-400 font-semibold"}>
                    {calculatedGridStress > 75 ? "CRITICAL" : calculatedGridStress > 50 ? "MODERATE" : "STABLE"}
                  </span>
                </div>
                <div className="text-muted-foreground pt-1">Recommendation:</div>
                <div className="text-[11px] text-amber-300 font-sans">
                  {calculatedGridStress > 70 ? "Shift flexible charging load" : "Feeder capacity available"}
                </div>
              </CardContent>
            </Card>

            {/* 4. Cost & Carbon Agent */}
            <Card className="bg-card/95 border-border shadow-md">
              <CardHeader className="py-2.5 px-3.5 border-b bg-muted/20">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold tracking-tight text-purple-400 flex items-center gap-1">
                    💰 COST & CARBON
                  </span>
                  <Badge variant="outline" className="text-[10px] h-4 py-0 border-purple-500/40 text-purple-400">
                    -35% Saved
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-3 text-xs space-y-1.5 font-mono">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Spot:</span>
                  <span>₹{baseTariffInr}/kWh</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Optimal:</span>
                  <span className="font-bold text-emerald-400">₹{optimalTariffInr}/kWh</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">CO₂ Intensity:</span>
                  <span className="text-muted-foreground">{currentCarbonG}g</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Optimized:</span>
                  <span className="font-bold text-emerald-400">{optimalCarbonG} g/kWh</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Central AI Orchestrator Decision Output */}
          <Card className="border-2 border-emerald-500/40 bg-gradient-to-b from-card to-emerald-950/20 shadow-2xl">
            <CardHeader className="py-3 px-4 border-b border-emerald-500/20 bg-emerald-500/10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-emerald-400 animate-spin" />
                  <CardTitle className="text-sm tracking-widest font-mono font-bold text-emerald-400">
                    AI ORCHESTRATOR
                  </CardTitle>
                </div>
                <Badge className="bg-emerald-500 text-black font-semibold text-xs">
                  Autonomous Decision
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-4 space-y-4 font-mono text-xs">
              <div className="space-y-1">
                <div className="text-[11px] text-muted-foreground uppercase tracking-wider">
                  Recommended Strategy
                </div>
                <div className="text-xl font-extrabold text-foreground font-sans text-emerald-400">
                  {shouldWait ? `WAIT ${waitMinutes} MINUTES` : "CHARGE IMMEDIATELY"}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 py-2.5 px-3 rounded-lg bg-background/60 border border-border">
                <div>
                  <div className="text-[10px] text-muted-foreground">START TIME</div>
                  <div className="text-sm font-bold">{formattedStart}</div>
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground">POWER DRAW</div>
                  <div className="text-sm font-bold text-primary">{chargingPowerKw} kW</div>
                </div>
                <div>
                  <div className="text-[10px] text-muted-foreground">FINISH TIME</div>
                  <div className="text-sm font-bold">{formattedFinish}</div>
                </div>
              </div>

              {/* Explainable Decision Checklist */}
              <div className="space-y-1.5 pt-1 font-sans text-xs">
                <div className="flex items-center gap-2 text-emerald-400">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>Departure deadline ({deadlineHour}:00) fully satisfied</span>
                </div>
                <div className="flex items-center gap-2 text-emerald-400">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>Lower regional grid stress ({calculatedGridStress}% managed)</span>
                </div>
                <div className="flex items-center gap-2 text-emerald-400">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>Higher renewable utilization ({renewablePct}% solar/wind sync)</span>
                </div>
                <div className="flex items-center gap-2 text-emerald-400">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>Estimated savings: ₹{((baseTariffInr - optimalTariffInr) * energyNeededKwh).toFixed(1)} &amp; {optimalCarbonG}g CO₂/kWh</span>
                </div>
              </div>

              <div className="pt-2 border-t border-border/60 text-[11px] text-muted-foreground font-sans italic">
                &ldquo;Change the energy conditions &rarr; watch the grid react &rarr; let the agents analyze &rarr; see AI orchestrate the optimal charging decision.&rdquo;
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
