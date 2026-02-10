"""GUVI-compatible response wrapper for MessageResponse."""
from pydantic import BaseModel
from typing import Literal


class GUVISimpleResponse(BaseModel):
    """
    Simplified response format required by GUVI.
    Format:
    {
      "status": "success",
      "reply": "Agent's response message"
    }
    """
    status: Literal["success", "error"] = "success"
    reply: str
