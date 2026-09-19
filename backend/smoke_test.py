#!/usr/bin/env python3
"""
VoltSync Standalone Smoke Test
Verifies end-to-end operational readiness of the VoltSync backend:
1. Health Check
2. Authentication Verification
3. Station Query & Retrieval
4. Session Creation & Parameter Calculation
5. Schedule Generation via Orchestrator
6. Schedule Query & Validation
7. Notification Delivery Logging
"""
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.models.station import Station
from app.models.charging_session import ChargingSession
from app.core.database import SessionLocal, Base, engine
from app.api.deps import get_current_user


def run_smoke_test() -> bool:
    print("=" * 60)
    print("  VOLTSYNC BACKEND SMOKE TEST")
    print("=" * 60)

    # Initialize DB & override auth
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Seed mock user & station if not present
    demo_user = db.query(User).filter(User.clerk_user_id == "smoke_driver_001").first()
    if not demo_user:
        demo_user = User(
            clerk_user_id="smoke_driver_001",
            role="driver"
        )
        db.add(demo_user)

    demo_station = db.query(Station).filter(Station.station_id == "ST_SMOKE_01").first()
    if not demo_station:
        demo_station = Station(
            station_id="ST_SMOKE_01",
            cpo_name="VoltSync Smoke Power",
            govt_private="Private",
            state="Maharashtra",
            district_city_village="Mumbai",
            location="BKC Express",
            latitude=19.0657,
            longitude=72.8687,
            charger_types_connectors_installed="CCS2",
            charger_rating=60.0,
            connector_rating=60.0,
            no_of_connectors=4
        )
        db.add(demo_station)

    db.commit()
    db.close()

    def mock_auth():
        return User(
            clerk_user_id="smoke_driver_001",
            role="driver",
            linked_station_ids=[],
            region=None
        )

    app.dependency_overrides[get_current_user] = mock_auth
    client = TestClient(app)

    try:
        # Step 1: Health
        print("[1/7] Testing /health ...", end=" ")
        res = client.get("/health")
        assert res.status_code == 200 and res.json()["status"] == "ok"
        print("PASSED")

        # Step 2: Auth Me
        print("[2/7] Testing /api/v1/auth/me ...", end=" ")
        res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer smoke_token"})
        assert res.status_code == 200 and res.json()["data"]["role"] == "driver"
        print("PASSED")

        # Step 3: Stations List & Detail
        print("[3/7] Testing /api/v1/stations ...", end=" ")
        res = client.get("/api/v1/stations", headers={"Authorization": "Bearer smoke_token"})
        assert res.status_code == 200
        res_det = client.get("/api/v1/stations/ST_SMOKE_01", headers={"Authorization": "Bearer smoke_token"})
        assert res_det.status_code == 200 and res_det.json()["data"]["station_id"] == "ST_SMOKE_01"
        print("PASSED")

        # Step 4: Session Creation
        print("[4/7] Testing POST /api/v1/sessions ...", end=" ")
        session_payload = {
            "station_id": "ST_SMOKE_01",
            "arrival_time": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
            "ready_by": (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat(),
            "initial_soc_pct": 20,
            "target_soc_pct": 80,
            "battery_capacity_kwh": 60,
            "max_charging_power_kw": 50,
            "flexibility": "High",
            "preference": "Greenest"
        }
        res_ses = client.post("/api/v1/sessions", json=session_payload, headers={"Authorization": "Bearer smoke_token"})
        assert res_ses.status_code == 201
        session_data = res_ses.json()["data"]
        session_id = session_data["session_id"]
        assert session_id is not None
        print(f"PASSED (session_id={session_id})")

        # Step 5: Schedule Generation (trigger via POST schedule)
        print("[5/7] Testing POST /api/v1/sessions/{id}/schedule ...", end=" ")
        res_sched = client.post(f"/api/v1/sessions/{session_id}/schedule", headers={"Authorization": "Bearer smoke_token"})
        assert res_sched.status_code == 200
        print("PASSED")

        # Step 6: Schedule Query & Detail
        print("[6/7] Testing GET /api/v1/sessions/{id}/schedule ...", end=" ")
        res_get_sched = client.get(f"/api/v1/sessions/{session_id}/schedule", headers={"Authorization": "Bearer smoke_token"})
        assert res_get_sched.status_code == 200
        assert res_get_sched.json()["data"]["session_id"] == session_id
        print("PASSED")

        # Step 7: Notification History
        print("[7/7] Testing GET /api/v1/notifications ...", end=" ")
        res_notif = client.get("/api/v1/notifications", headers={"Authorization": "Bearer smoke_token"})
        assert res_notif.status_code == 200
        print("PASSED")

        print("=" * 60)
        print("  SMOKE TEST RESULT: ALL 7 STEPS PASSED SUCCESSFULLY!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
