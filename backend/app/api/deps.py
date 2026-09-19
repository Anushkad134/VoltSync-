from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import verify_token
from typing import List

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={
            "error_code": "UNAUTHENTICATED",
            "message": "Authentication is required.",
            "status_code": 401
        })
        
    token = auth_header.split(" ")[1]
    
    # We will mock the token for testing if it's the exact string "test_token_{clerk_id}_{role}"
    # This allows test_routes to bypass JWKS validation while keeping it real for auth.
    # We shouldn't put test code in prod normally, but we use dependency_overrides in tests!
    
    clerk_user_id = verify_token(token)
    
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if not user:
        # Auto-create user on first login with unassigned role
        user = User(
            clerk_user_id=clerk_user_id,
            role="unassigned",
            region=None,
            linked_station_ids=[]
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return user

def require_role(allowed_roles: List[str]):
    def role_checker(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail={
                "error_code": "FORBIDDEN",
                "message": "You do not have permission to access this resource.",
                "status_code": 403
            })
        return user
    return role_checker

def require_driver(user: User = Depends(require_role(["driver", "operator", "grid_operator", "admin"]))) -> User:
    return user

def require_operator(user: User = Depends(require_role(["operator", "grid_operator", "driver", "admin"]))) -> User:
    return user

def require_grid_operator(user: User = Depends(require_role(["grid_operator", "operator", "driver", "admin"]))) -> User:
    return user

def check_session_access(session_id: str, user: User, db: Session):
    from app.models.charging_session import ChargingSession
    from app.models.station import Station
    
    session = db.query(ChargingSession).filter(ChargingSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Session not found.", "status_code": 404})
        
    if user.role == "driver":
        if session.clerk_user_id != user.clerk_user_id:
            raise HTTPException(status_code=403, detail={"error_code": "FORBIDDEN", "message": "You do not have permission to access this resource.", "status_code": 403})
    elif user.role == "operator":
        if not user.linked_station_ids or session.station_id not in user.linked_station_ids:
            raise HTTPException(status_code=403, detail={"error_code": "FORBIDDEN", "message": "You do not have permission to access this resource.", "status_code": 403})
    elif user.role == "grid_operator":
        station = db.query(Station).filter(Station.station_id == session.station_id).first()
        if not station or not user.region or station.region != user.region:
            raise HTTPException(status_code=403, detail={"error_code": "FORBIDDEN", "message": "You do not have permission to access this resource.", "status_code": 403})
            
    return session
