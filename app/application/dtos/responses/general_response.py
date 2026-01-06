from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")

class ErrorDTO(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None

class GeneralResponse(BaseModel, Generic[T]):
    success: bool
    message: Optional[str] = None
    data: Optional[T] = None
    error: Optional[ErrorDTO] = None
