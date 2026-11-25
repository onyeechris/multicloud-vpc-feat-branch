from pydantic import BaseModel
from typing import Any, Dict


class StackResponse(BaseModel):
    status: str
    stack: str
    outputs: Dict[str, Any] = {}
