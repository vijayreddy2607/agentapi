"""Student agent - Young, tech-aware but naive persona with intelligent fallback system."""
from app.agents.base_agent import BaseAgent
from app.prompts.student_persona import (
    STUDENT_SYSTEM_PROMPT, 
    STUDENT_FEW_SHOT_EXAMPLES,
    detect_student_scam_type,
    get_student_fallback_reply
)
import random
import logging

logger = logging.getLogger(__name__)


class StudentAgent(BaseAgent):
    """Student persona - Naive college student targeted by youth scams.
    
    Features:
    - Scam type detection (fake jobs, loans, investments, scholarships, gigs)
    - Two-message fallback templates (turns 1-2) for fast, consistent responses
    - Groq LLM for later turns (3+) with full context
    - Natural Hinglish with slang, emojis, typos
    """
    
    def __init__(self):
        super().__init__(persona_name="Arjun (Student)")
        self.detected_scam_type = None  # Cache scam type for session
    
    def get_system_prompt(self) -> str:
        """Return Student's enhanced system prompt."""
        return STUDENT_SYSTEM_PROMPT
    
    def get_few_shot_examples(self) -> list:
        """Return Student's conversation examples."""
        return STUDENT_FEW_SHOT_EXAMPLES
    
    def _get_stateful_fallback(self, scammer_message: str, turn_count: int) -> str:
        """Student's intelligent stateful fallback using scam type detection.
        
        Strategy:
        - Turn 1-2: Use scam-specific templates (fast, consistent trust-building)
        - Turn 3+: Return None to trigger LLM (dynamic, context-aware)
        
        Args:
            scammer_message: Latest message from scammer
            turn_count: Current conversation turn (0-indexed)
            
        Returns:
            Template response or None (triggers LLM)
        """
        # For turns 1-2, use fallback templates
        if turn_count <= 1:
            # Detect scam type if not already cached
            if self.detected_scam_type is None:
                self.detected_scam_type = detect_student_scam_type(scammer_message)
                logger.info(f"🎯 Detected scam type for student: {self.detected_scam_type}")
            
            # Get fallback reply (turn_count is 0-indexed, template uses 1-indexed)
            template_turn = turn_count + 1
            reply = get_student_fallback_reply(
                scam_type=self.detected_scam_type,
                turn_number=template_turn,
                last_scammer_message=scammer_message
            )
            
            if reply:
                logger.info(f"✅ Using fallback template (turn {template_turn}, type: {self.detected_scam_type})")
                return reply
        
        # Turn 3+: Use LLM for dynamic, context-aware responses
        logger.info(f"🤖 Turn {turn_count + 1}: Handing off to LLM for dynamic response")
        return None  # Triggers LLM in base_agent
