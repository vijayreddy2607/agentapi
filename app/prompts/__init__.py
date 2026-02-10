"""Prompts package."""
from app.prompts.scam_detection import SCAM_DETECTION_SYSTEM_PROMPT
from app.prompts.uncle_persona import UNCLE_SYSTEM_PROMPT, UNCLE_FEW_SHOT_EXAMPLES
from app.prompts.worried_persona import WORRIED_SYSTEM_PROMPT, WORRIED_FEW_SHOT_EXAMPLES
from app.prompts.techsavvy_persona import TECHSAVVY_SYSTEM_PROMPT, TECHSAVVY_FEW_SHOT_EXAMPLES

__all__ = [
    "SCAM_DETECTION_SYSTEM_PROMPT",
    "UNCLE_SYSTEM_PROMPT",
    "UNCLE_FEW_SHOT_EXAMPLES",
    "WORRIED_SYSTEM_PROMPT",
    "WORRIED_FEW_SHOT_EXAMPLES",
    "TECHSAVVY_SYSTEM_PROMPT",
    "TECHSAVVY_FEW_SHOT_EXAMPLES",
]
