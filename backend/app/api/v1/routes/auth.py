from app.models.user import User
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user, require_driver, require_operator, require_grid_operator, get_db
from app.schemas.common import DataResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

router = APIRouter()

class AuthMeResponse(BaseModel):
    clerk_user_id: str
    role: str
    region: Optional[str] = None
    linked_station_ids: Optional[List[str]] = []

class UpdateRoleRequest(BaseModel):
    role: str
    region: Optional[str] = None
    linked_station_ids: Optional[List[str]] = []

@router.get("/me", response_model=DataResponse[AuthMeResponse])
def get_me(user: User = Depends(get_current_user)):
    return DataResponse(data=AuthMeResponse(
        clerk_user_id=user.clerk_user_id,
        role=user.role,
        region=user.region,
        linked_station_ids=user.linked_station_ids or []
    ))

@router.put("/me/role", response_model=DataResponse[AuthMeResponse])
def update_my_role(
    request: UpdateRoleRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user role and related fields (for testing/demo purposes)"""
    if request.role not in ["driver", "operator", "grid_operator"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail={
            "error_code": "INVALID_ROLE",
            "message": "Role must be one of: driver, operator, grid_operator",
            "status_code": 400
        })
    
    user.role = request.role
    user.region = request.region
    user.linked_station_ids = request.linked_station_ids or []
    
    db.commit()
    db.refresh(user)
    
    return DataResponse(data=AuthMeResponse(
        clerk_user_id=user.clerk_user_id,
        role=user.role,
        region=user.region,
        linked_station_ids=user.linked_station_ids or []
    ))
