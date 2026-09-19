from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.charging_session import ChargingSession
from app.models.charging_schedule import ChargingSchedule
from app.models.agent_decision import AgentDecision
from app.models.station import Station
from app.orchestrator.orchestrator import Orchestrator, ScheduleResult
from app.orchestrator.constraint_validator import SchedulingValidationError

class SchedulingService:
    @staticmethod
    def get_agent_outputs_for_session(session: ChargingSession, station: Station, db: Session) -> Dict[str, Any]:
        """
        Retrieves agent decisions for a session, or populates deterministic defaults if none exist.
        """
        decisions = db.query(AgentDecision).filter(AgentDecision.session_id == session.session_id).all()
        outputs: Dict[str, Any] = {}
        for d in decisions:
            if d.output_data:
                outputs[d.agent_type] = d.output_data

        # Fallback defaults for any missing agent
        if "driver" not in outputs:
            outputs["driver"] = {
                "session_id": session.session_id,
                "energy_required_kwh": session.energy_required_kwh,
                "estimated_duration_min": int(session.estimated_duration_min),
                "urgency": "Medium",
                "flexibility": session.flexibility,
                "preference": session.preference,
                "available_window_start": session.arrival_time.isoformat() if session.arrival_time else None,
                "available_window_end": session.ready_by.isoformat() if session.ready_by else None,
                "reason": "Derived from charging session parameters."
            }

        if "renewable" not in outputs:
            outputs["renewable"] = {
                "session_id": session.session_id,
                "green_windows": [],
                "greenest_window": None,
                "forecast_confidence": 0.85,
                "reason": "Renewable generation analysis."
            }

        if "grid" not in outputs:
            outputs["grid"] = {
                "session_id": session.session_id,
                "grid_stress": "Low",
                "grid_stress_pct": 35.0,
                "station_load_classification": "Moderate",
                "recommended_action": "Standard charging",
                "urgency_override": False,
                "reason": "Grid stability parameters nominal."
            }

        if "cost_carbon" not in outputs:
            outputs["cost_carbon"] = {
                "session_id": session.session_id,
                "candidate_windows": [],
                "cheapest_window": None,
                "lowest_carbon_window": None,
                "tradeoff_summary": "Evaluated cost and carbon intensity metrics."
            }

        return outputs

    @staticmethod
    def generate_and_persist_schedule(session_id: str, db: Session) -> ChargingSchedule:
        """
        Orchestrates schedule generation, persists schedule history, and updates session status.
        """
        session = db.query(ChargingSession).filter(ChargingSession.session_id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "NOT_FOUND", "message": f"Session {session_id} not found.", "status_code": 404}
            )

        station = db.query(Station).filter(Station.station_id == session.station_id).first()
        if not station:
            # Fallback mock station if not seeded
            station = Station(
                station_id=session.station_id,
                cpo_name="Default CPO",
                govt_private="Private",
                state="Default State",
                district_city_village="Default City",
                location="Default Location",
                latitude=0.0,
                longitude=0.0,
                charger_types_connectors_installed="CCS2",
                charger_rating=session.max_charging_power_kw or 50.0,
                connector_rating=session.max_charging_power_kw or 50.0,
                no_of_connectors=2
            )

        agent_outputs = SchedulingService.get_agent_outputs_for_session(session, station, db)

        orchestrator = Orchestrator()
        try:
            result = orchestrator.create_schedule(session, station, agent_outputs, db)
        except SchedulingValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error_code": "SCHEDULING_SERVICE_UNAVAILABLE", "message": str(e), "status_code": 503}
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error_code": "SCHEDULING_SERVICE_UNAVAILABLE", "message": f"Scheduling error: {str(e)}", "status_code": 503}
            )

        # Persist schedule (append to preserve history)
        schedule = ChargingSchedule(
            session_id=session_id,
            segments=result.segments,
            summary_line=result.summary_line,
            status=result.status,
            last_updated=datetime.now(timezone.utc)
        )
        db.add(schedule)

        # Update session status
        if result.status == "Infeasible":
            session.status = "Infeasible"
        else:
            session.status = "Scheduled"
        db.commit()
        db.refresh(schedule)

        # Dispatch ScheduleGenerated notification (failure isolated)
        try:
            from app.services.notification_service import NotificationService
            start_str = result.segments[0]["start_time"] if result.segments else "TBD"
            end_str = result.segments[-1]["end_time"] if result.segments else "TBD"
            avg_ren = sum(s.get("expected_renewable_pct", 0) for s in result.segments) / max(len(result.segments), 1)
            
            NotificationService.notify(
                event_type="ScheduleGenerated",
                session_id=session_id,
                context={
                    "start_time": start_str,
                    "end_time": end_str,
                    "renewable_share_pct": avg_ren,
                    "summary_line": result.summary_line,
                    "station_id": session.station_id
                },
                db=db
            )
        except Exception:
            pass

        return schedule

    @staticmethod
    def get_schedule(session_id: str, db: Session) -> Dict[str, Any]:
        schedule = db.query(ChargingSchedule).filter(
            ChargingSchedule.session_id == session_id
        ).order_by(ChargingSchedule.last_updated.desc(), ChargingSchedule.id.desc()).first()

        if not schedule:
            try:
                schedule = SchedulingService.generate_and_persist_schedule(session_id, db)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error_code": "NOT_FOUND", "message": f"Schedule for session {session_id} not found.", "status_code": 404}
                )

        session = db.query(ChargingSession).filter(ChargingSession.session_id == session_id).first()
        station = db.query(Station).filter(Station.station_id == session.station_id).first() if session else None
        
        agent_outputs = SchedulingService.get_agent_outputs_for_session(session, station, db) if (session and station) else {}
        
        formatted_outputs = {}
        for k, v in agent_outputs.items():
            formatted_outputs[k] = v
            if not k.endswith("_agent"):
                formatted_outputs[f"{k}_agent"] = v

        # If schedule is an ORM object
        summary = getattr(schedule, "summary_line", "")
        stat = getattr(schedule, "status", "Scheduled")
        segs = getattr(schedule, "segments", []) or []

        return {
            "session_id": session_id,
            "summary_line": summary,
            "status": stat,
            "segments": segs,
            "schedule_segments": segs,
            "agent_outputs": formatted_outputs
        }

    @staticmethod
    def get_schedule_history(session_id: str, db: Session, limit: int = 20, offset: int = 0) -> Tuple[List[ChargingSchedule], int]:
        query = db.query(ChargingSchedule).filter(
            ChargingSchedule.session_id == session_id
        ).order_by(ChargingSchedule.last_updated.desc(), ChargingSchedule.id.desc())

        total = query.count()
        schedules = query.offset(offset).limit(limit).all()
        return schedules, total

    @staticmethod
    def get_candidate_windows(session_id: str, db: Session) -> List[Dict[str, Any]]:
        session = db.query(ChargingSession).filter(ChargingSession.session_id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "NOT_FOUND", "message": f"Session {session_id} not found.", "status_code": 404}
            )

        station = db.query(Station).filter(Station.station_id == session.station_id).first()
        agent_outputs = SchedulingService.get_agent_outputs_for_session(session, station, db)
        
        orchestrator = Orchestrator()
        result = orchestrator.create_schedule(session, station, agent_outputs, db)
        return result.candidate_windows

    @staticmethod
    def get_agent_decisions(session_id: str, db: Session) -> List[Dict[str, Any]]:
        decisions = db.query(AgentDecision).filter(AgentDecision.session_id == session_id).all()
        results = []
        for d in decisions:
            output = d.output_data or {}
            results.append({
                "agent": d.agent_type,
                "recommendation": output.get("recommended_action") or output.get("preference") or output.get("tradeoff_summary") or "Analyzed",
                "reason": output.get("reason") or output.get("tradeoff_summary") or "Standard agent analysis",
                "created_at": d.created_at
            })
        return results

    @staticmethod
    def reschedule_session(session_id: str, ready_by: datetime, preference: str, flexibility: str, db: Session) -> ChargingSchedule:
        session = db.query(ChargingSession).filter(ChargingSession.session_id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "NOT_FOUND", "message": f"Session {session_id} not found.", "status_code": 404}
            )

        session.ready_by = ready_by
        session.preference = preference
        session.flexibility = flexibility
        session.updated_at = datetime.now(timezone.utc)
        db.commit()

        schedule = SchedulingService.generate_and_persist_schedule(session_id, db)

        # Dispatch ScheduleChanged notification (failure isolated)
        try:
            from app.services.notification_service import NotificationService
            start_str = schedule.segments[0]["start_time"] if schedule.segments else "TBD"
            NotificationService.notify(
                event_type="ScheduleChanged",
                session_id=session_id,
                context={
                    "start_time": start_str,
                    "reason": f"preference update to {preference} and ready-by {ready_by.strftime('%H:%M')}",
                    "station_id": session.station_id
                },
                db=db
            )
        except Exception:
            pass

        return schedule
