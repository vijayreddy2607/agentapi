"""Tech-savvy user persona agent implementation."""
from app.agents.base_agent import BaseAgent
from app.prompts import TECHSAVVY_SYSTEM_PROMPT, TECHSAVVY_FEW_SHOT_EXAMPLES


class TechSavvyAgent(BaseAgent):
    """Agent with Tech-Savvy persona - educated, skeptical but curious."""
    
    def __init__(self):
        super().__init__(persona_name="Tech-Savvy User")
    
    def get_system_prompt(self) -> str:
        """Return Tech-Savvy persona system prompt."""
        return TECHSAVVY_SYSTEM_PROMPT
    
    def get_few_shot_examples(self) -> list[dict[str, str]]:
        """Return Tech-Savvy persona few-shot examples."""
        return TECHSAVVY_FEW_SHOT_EXAMPLES
