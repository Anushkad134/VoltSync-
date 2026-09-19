from typing import Dict, Any, Optional

SUPPORTED_EVENT_TYPES = {
    "SessionCreated",
    "ScheduleGenerated",
    "ScheduleChanged",
    "ChargingStarted",
    "ChargingDelayed",
    "ProgressUpdate",
    "ReadyEarly",
    "ReadyOnTime",
    "ChargingCompleted",
    "StationAlert",
    "GridAlert",
}

class MessageBuilder:
    @staticmethod
    def build_message(event_type: str, context: Optional[Dict[str, Any]] = None) -> str:
        ctx = context or {}

        if event_type == "SessionCreated":
            station_id = ctx.get("station_id", "ST-001")
            session_id = ctx.get("session_id", "SES-001")
            return f"⚡ VoltSync: Your charging session {session_id} has been created at Station {station_id}. We're analyzing the best charging window for you."

        elif event_type == "ScheduleGenerated":
            start_time = ctx.get("start_time", "11:00")
            end_time = ctx.get("end_time", "13:00")
            ren_pct = ctx.get("renewable_share_pct", ctx.get("expected_renewable_pct", 80.0))
            summary = ctx.get("summary_line", "")
            summary_suffix = f" {summary}" if summary else ""
            return f"🌱 VoltSync: Your charging schedule is ready. Charging is planned for {start_time}–{end_time} with an expected renewable share of {ren_pct:.0f}%.{summary_suffix}".strip()

        elif event_type == "ScheduleChanged":
            start_time = ctx.get("start_time", "11:30")
            reason = ctx.get("reason", "improved renewable availability")
            return f"🔄 VoltSync: Your charging schedule has changed. Charging now starts at {start_time} due to {reason}."

        elif event_type == "ChargingStarted":
            station_id = ctx.get("station_id", "ST-001")
            power_kw = ctx.get("power_level_kw", ctx.get("power_kw", 50.0))
            return f"🔋 VoltSync: Charging has started at Station {station_id}. Power: {power_kw:.0f} kW."

        elif event_type == "ChargingDelayed":
            reason = ctx.get("reason", "high grid demand")
            start_time = ctx.get("start_time", "12:00")
            end_time = ctx.get("end_time", "13:30")
            return f"⏳ VoltSync: Charging has been delayed due to {reason}. Your updated charging window is {start_time}–{end_time}."

        elif event_type == "ProgressUpdate":
            progress_pct = ctx.get("progress_pct", 65.0)
            remaining_min = ctx.get("remaining_min", ctx.get("estimated_remaining_time_min", 24))
            return f"🔋 VoltSync: Charging progress: {progress_pct:.0f}% complete. Estimated remaining time: {remaining_min} minutes."

        elif event_type == "ReadyEarly":
            return "✅ VoltSync: Your vehicle is ready earlier than expected. Charging can begin now."

        elif event_type == "ReadyOnTime":
            ready_by = ctx.get("ready_by", "your requested time")
            return f"✅ VoltSync: Your vehicle is on track to be ready by {ready_by}."

        elif event_type == "ChargingCompleted":
            energy_kwh = ctx.get("energy_delivered_kwh", ctx.get("energy_kwh", 30.0))
            ren_pct = ctx.get("renewable_share_pct", ctx.get("expected_renewable_pct", 80.0))
            return f"🎉 VoltSync: Charging completed. Energy delivered: {energy_kwh:.1f} kWh. Estimated renewable share: {ren_pct:.0f}%."

        elif event_type == "StationAlert":
            station_id = ctx.get("station_id", "ST-001")
            available = ctx.get("available_connectors", 2)
            total = ctx.get("total_connectors", 6)
            return f"⚠️ VoltSync Station Alert: Station {station_id} has reduced availability. Available connectors: {available}/{total}."

        elif event_type == "GridAlert":
            region = ctx.get("region", "Gujarat-West")
            stress_level = ctx.get("stress_level", "Critical")
            stress_pct = ctx.get("grid_stress_pct", 95.0)
            return f"⚠️ VoltSync Grid Alert: Region {region} has reached {stress_level} grid stress at {stress_pct:.0f}%. Charging load reduction is recommended."

        else:
            return f"⚡ VoltSync Notification: {event_type} event recorded."
