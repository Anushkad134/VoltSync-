from fastapi import APIRouter
from app.api.v1.routes import (
    auth, stations, sessions, grid, renewable, pricing, operator, grid_operator, whatsapp, notifications
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(stations.router, prefix="/stations", tags=["Stations"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(grid.router, prefix="/grid", tags=["Grid"])
api_router.include_router(renewable.router, prefix="/renewable", tags=["Renewable"])
api_router.include_router(pricing.router, prefix="/pricing", tags=["Pricing"])
api_router.include_router(operator.router, prefix="/operator", tags=["Operator"])
api_router.include_router(grid_operator.router, prefix="/grid-operator", tags=["Grid Operator"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["WhatsApp"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

@api_router.get("/health")
def health_check():
    return {"status": "ok", "message": "VoltSync backend is healthy"}
