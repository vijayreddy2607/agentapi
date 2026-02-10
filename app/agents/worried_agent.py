"""Worried person persona agent implementation."""
from app.agents.base_agent import BaseAgent
from app.prompts import WORRIED_SYSTEM_PROMPT, WORRIED_FEW_SHOT_EXAMPLES


class WorriedAgent(BaseAgent):
    """Agent with Worried persona - anxious professional, cooperative but nervous."""
    
    def __init__(self):
        super().__init__(persona_name="Worried Person")
    
    def get_system_prompt(self) -> str:
        """Return Worried persona system prompt."""
        return WORRIED_SYSTEM_PROMPT
    
    def get_few_shot_examples(self) -> list[dict[str, str]]:
        """Return Worried persona few-shot examples."""
        return WORRIED_FEW_SHOT_EXAMPLES
