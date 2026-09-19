from typing import Generic, TypeVar, List, Optional, Dict, Any
from pydantic import BaseModel

T = TypeVar("T")

class Pagination(BaseModel):
    limit: int
    offset: int
    total: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: Pagination

class DataResponse(BaseModel, Generic[T]):
    data: T

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    status_code: int
    field_errors: Optional[Dict[str, str]] = None
