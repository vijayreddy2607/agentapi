"""Student persona agent implementation."""
from app.agents.base_agent import BaseAgent
from app.prompts import STUDENT_SYSTEM_PROMPT, STUDENT_FEW_SHOT_EXAMPLES


class StudentAgent(BaseAgent):
    """Agent with Student persona - excited, naive college student."""

    def __init__(self):
        super().__init__(persona_name="Student")

    def get_system_prompt(self) -> str:
        """Return Student persona system prompt."""
        return STUDENT_SYSTEM_PROMPT

    def get_few_shot_examples(self) -> list[dict[str, str]]:
        """Return Student few-shot examples."""
        return STUDENT_FEW_SHOT_EXAMPLES
