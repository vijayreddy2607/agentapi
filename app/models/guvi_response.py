"""GUVI-compatible response wrapper for MessageResponse."""
from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any


class GUVISimpleResponse(BaseModel):
    """
    Simplified response format required by GUVI.
    Format:
    {
      "status": "success",
      "reply": "Agent's response message",
      "intelligence_log": {...}  # optional internal field for evaluation
    }
    """
    status: Literal["success", "error"] = "success"
    reply: str
    intelligence_log: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True}

    def model_dump(self, **kwargs):
        """Exclude None fields by default to keep GUVI compliance."""
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)
