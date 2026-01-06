from pydantic import BaseModel, Field

class QRReadRequestDTO(BaseModel):
    raw: str = Field(..., min_length=1)
