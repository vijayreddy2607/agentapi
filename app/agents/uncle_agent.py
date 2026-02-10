"""Uncle persona agent implementation."""
from app.agents.base_agent import BaseAgent
from app.prompts import UNCLE_SYSTEM_PROMPT, UNCLE_FEW_SHOT_EXAMPLES


class UncleAgent(BaseAgent):
    """Agent with Uncle persona - friendly, semi-tech-savvy, concerned about finances."""
    
    def __init__(self):
        super().__init__(persona_name="Uncle")
    
    def get_system_prompt(self) -> str:
        """Return Uncle persona system prompt."""
        return UNCLE_SYSTEM_PROMPT
    
    def get_few_shot_examples(self) -> list[dict[str, str]]:
        """Return Uncle persona few-shot examples."""
        return UNCLE_FEW_SHOT_EXAMPLES
