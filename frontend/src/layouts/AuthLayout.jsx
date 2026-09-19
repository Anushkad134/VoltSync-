import { Outlet } from "react-router-dom";
import { Zap } from "lucide-react";

export default function AuthLayout() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-900">
      <div className="absolute top-8 left-8 flex items-center gap-2 text-white">
        <Zap className="w-8 h-8 text-emerald-400" />
        <span className="text-2xl font-bold">VoltSync</span>
      </div>
      <Outlet />
    </div>
  );
}
