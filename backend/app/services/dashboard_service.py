from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.station import Station
from app.models.charging_session import ChargingSession
from app.models.grid_demand import GridDemand
from app.models.renewable_generation import RenewableGeneration
from app.models.notification_log import NotificationLog
from app.schemas.operator import OperatorDashboardResponse, GridOperatorDashboardResponse, ChargingLoadResponse
from app.services.station_service import StationService
from app.services.queue_service import QueueService

class DashboardService:
    @staticmethod
    def get_operator_dashboard(user: User, db: Session) -> OperatorDashboardResponse:
        from app.schemas.operator import OperatorStationData, OperatorSessionData
        from datetime import datetime, timedelta
        
        linked_ids = user.linked_station_ids or []
        
        linked_ids = user.linked_station_ids or []
        query = db.query(Station)
        if linked_ids:
            query = query.filter(Station.station_id.in_(linked_ids))
        stations = query.all()

        station_count = len(stations)
        available_cnt = 0
        occupied_cnt = 0
        offline_cnt = 0
        total_load_kw = 0.0

        # Build station data list for frontend
        stations_data = []
        for s in stations:
            status_str, avail, total = StationService.get_station_availability(s, db)
            
            if status_str == "Available":
                available_cnt += 1
                status = "ONLINE"
            elif status_str in ["Busy", "Limited"]:
                occupied_cnt += 1
                status = "DEGRADED"
            else:
                offline_cnt += 1
                status = "OFFLINE"
            
            station_load = QueueService.calculate_station_load(s.station_id, db)
            total_load_kw += station_load
            
            queue_len = len(QueueService.get_station_queue(s.station_id, db))
            
            # Get active sessions count for this station
            active_sess_count = db.query(ChargingSession).filter(
                ChargingSession.station_id == s.station_id,
                ChargingSession.status.in_(["Charging", "InProgress"])
            ).count()
            
            stations_data.append(OperatorStationData(
                id=s.station_id,
                name=f"{s.cpo_name} - {s.location}" if s.cpo_name else s.location,
                location=s.location,
                status=status,
                active_sessions=active_sess_count,
                current_power_draw=station_load,
                total_ports=s.no_of_connectors or 1,
                available_ports=avail,
                max_power_kw=s.charger_rating or 0,
                queue_length=queue_len,
            ))

        station_ids = [s.station_id for s in stations]
        active_sessions = db.query(ChargingSession).filter(
            ChargingSession.station_id.in_(station_ids),
            ChargingSession.status.in_(["Charging", "InProgress"])
        ).count() if station_ids else 0

        queued_sessions = db.query(ChargingSession).filter(
            ChargingSession.station_id.in_(station_ids),
            ChargingSession.status.in_(["Queued", "Created", "Scheduled"])
        ).count() if station_ids else 0

        avg_queue = round(queued_sessions / max(station_count, 1), 2)

        # Region metrics
        region = f"{stations[0].state} - {stations[0].district_city_village}".strip() if stations else "Default"
        latest_grid = db.query(GridDemand).filter(GridDemand.region == region).order_by(GridDemand.timestamp.desc()).first()
        latest_ren = db.query(RenewableGeneration).filter(RenewableGeneration.region == region).order_by(RenewableGeneration.timestamp.desc()).first()

        grid_stress = latest_grid.grid_stress_pct if latest_grid else 35.0
        renewable_share = latest_ren.renewable_share_pct if latest_ren else 45.0

        # Get queued sessions data for the queue table
        queued_session_data = []
        if station_ids:
            queued = db.query(ChargingSession).filter(
                ChargingSession.station_id.in_(station_ids),
                ChargingSession.status.in_(["Queued", "Created", "Scheduled"])
            ).limit(20).all()
            
            for qs in queued:
                queued_session_data.append(OperatorSessionData(
                    id=qs.session_id,
                    session_id=qs.session_id,
                    status=qs.status,
                    target_soc=qs.target_soc_pct,
                    estimated_wait_minutes=qs.estimated_duration_min,
                    created_at=qs.created_at,
                ))

        # Generate mock power consumption history (last 24 hours)
        power_history = []
        now = datetime.now()
        for i in range(24):
            timestamp = now - timedelta(hours=23-i)
            # Generate somewhat realistic power data with peak hours
            hour = timestamp.hour
            base_power = 50  # Base load
            peak_factor = 1.5 if 8 <= hour <= 20 else 0.7  # Peak during day
            power = base_power * peak_factor * station_count + (total_load_kw * 0.1)
            power_history.append({
                "time": timestamp.strftime("%H:00"),
                "power": round(power, 2),
                "timestamp": timestamp.isoformat(),
            })

        return OperatorDashboardResponse(
            station_count=station_count,
            available_stations=available_cnt,
            occupied_stations=occupied_cnt,
            offline_stations=offline_cnt,
            total_active_sessions=active_sessions,
            queued_sessions=queued_sessions,
            average_queue_length=avg_queue,
            current_charging_load_kw=round(total_load_kw, 2),
            relevant_grid_stress_pct=round(grid_stress, 2),
            renewable_share_pct=round(renewable_share, 2),
            stations=stations_data,
            queued_sessions_list=queued_session_data,
            power_consumption_history=power_history,
        )

    @staticmethod
    def get_grid_operator_dashboard(user: User, db: Session) -> GridOperatorDashboardResponse:
        region = user.region or "Maharashtra - Mumbai"

        latest_grid = db.query(GridDemand).filter(GridDemand.region == region).order_by(GridDemand.timestamp.desc()).first()
        latest_ren = db.query(RenewableGeneration).filter(RenewableGeneration.region == region).order_by(RenewableGeneration.timestamp.desc()).first()

        # Regional charging load
        stations = db.query(Station).all()
        regional_stations = [
            s for s in stations
            if region in f"{s.state} - {s.district_city_village}" or s.state in region
        ]
        total_load_kw = sum(QueueService.calculate_station_load(s.station_id, db) for s in regional_stations)

        alerts_count = db.query(NotificationLog).filter(
            NotificationLog.event_type == "GridAlert"
        ).count()

        return GridOperatorDashboardResponse(
            region=region,
            current_demand_mw=latest_grid.demand_mw if latest_grid else 1200.0,
            peak_demand_mw=latest_grid.peak_demand_mw if latest_grid else 1500.0,
            available_capacity_mw=latest_grid.available_capacity_mw if latest_grid else 1800.0,
            reserve_margin_mw=latest_grid.reserve_margin_mw if latest_grid else 600.0,
            grid_stress_pct=latest_grid.grid_stress_pct if latest_grid else 35.0,
            renewable_share_pct=latest_ren.renewable_share_pct if latest_ren else 45.0,
            active_charging_load_kw=round(total_load_kw, 2),
            active_grid_alerts=alerts_count
        )

    @staticmethod
    def get_charging_load(station_id: str, db: Session) -> ChargingLoadResponse:
        station = StationService.get_station(station_id, db)
        active_sessions = db.query(ChargingSession).filter(
            ChargingSession.station_id == station_id,
            ChargingSession.status.in_(["Charging", "InProgress"])
        ).count()

        charging_load = QueueService.calculate_station_load(station_id, db)
        queue_len = len(QueueService.get_station_queue(station_id, db))
        region = f"{station.state} - {station.district_city_village}".strip()

        return ChargingLoadResponse(
            station_id=station_id,
            region=region,
            active_sessions=active_sessions,
            charging_load_kw=charging_load,
            queue_length=queue_len
        )
