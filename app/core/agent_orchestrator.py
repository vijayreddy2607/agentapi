"""Agent orchestrator for selecting and managing agents."""
from typing import Literal
from app.agents import UncleAgent, WorriedAgent, TechSavvyAgent, AuntyAgent, StudentAgent, BaseAgent
from app.core.session_manager import Session
import logging

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates agent selection and management."""
    
    def __init__(self):
        # Agent pool - NOW WITH 5 PERSONAS!
        self.agent_pool = {
            "uncle": UncleAgent,
            "worried": WorriedAgent,
            "techsavvy": TechSavvyAgent,
            "aunty": AuntyAgent,
            "student": StudentAgent
        }
    
    def get_agent(
        self,
        agent_type: Literal["uncle", "worried", "techsavvy", "aunty", "student"],
        session: Session
    ) -> BaseAgent:
        """
        Get or create agent for session.
        
        Args:
            agent_type: Type of agent to use
            session: Current session
        
        Returns:
            Agent instance
        """
        # If session already has an agent, return it (maintain consistency)
        if session.agent is not None:
            logger.info(f"Reusing existing {session.agent_type} agent for session {session.session_id}")
            return session.agent
        
        # Create new agent
        agent_class = self.agent_pool.get(agent_type, UncleAgent)
        agent = agent_class()
        
        # Store in session
        session.agent = agent
        session.agent_type = agent_type
        
        logger.info(f"Created new {agent_type} agent for session {session.session_id}")
        return agent
    
    def get_conversation_phase(self, turn_count: int) -> str:
        """
        Determine conversation phase based on turn count.
        
        Phases:
        - build_trust (1-3 turns): Initial engagement, appear naive
        - extract_info (4-7 turns): Ask questions, extract intelligence  
        - verify_details (8-10 turns): Challenge scammer, request proof
        - stall_tactics (11+ turns): Waste time, create obstacles
        
        Args:
            turn_count: Number of messages exchanged
            
        Returns:
            Phase name
        """
        if turn_count <= 3:
            return "build_trust"
        elif turn_count <= 7:
            return "extract_info"
        elif turn_count <= 10:
            return "verify_details"
        else:
            return "stall_tactics"

    
    async def generate_response(
        self,
        session: Session,
        scammer_message: str,
        conversation_history: list = None,
        rl_action: str = None  # NEW: RL action
    ) -> str:
        """
        Generate agent response for scammer message.
        
        Args:
            session: Current session
            scammer_message: Latest scammer message
            conversation_history: Previous messages
            rl_action: RL-selected action strategy (optional)
        
        Returns:
            Agent's response
        """
        if session.agent is None:
            raise ValueError(f"No agent assigned to session {session.session_id}")
        
        # Determine conversation phase
        phase = self.get_conversation_phase(session.total_messages)
        logger.info(f"📊 Conversation phase: {phase} (turn {session.total_messages})")
        
        # Get RL strategy prompt if action provided
        rl_strategy_prompt = ""
        if rl_action:
            from app.rl import RLAgent
            rl_agent = RLAgent()
            rl_strategy_prompt = rl_agent.get_action_prompt(rl_action, session.scam_type)
            
            # Add phase-specific guidance
            phase_guidance = {
                "build_trust": "\n\nPHASE: Build Trust - Appear naive and interested. Don't be too suspicious yet.",
                "extract_info": "\n\nPHASE: Extract Info - Ask questions to gather intelligence. Show some skepticism.",
                "verify_details": "\n\nPHASE: Verify Details - Challenge the scammer. Request proof and credentials.",
                "stall_tactics": "\n\nPHASE: Stall Tactics - Waste time with obstacles, delays, and confusion."
            }
            rl_strategy_prompt += phase_guidance.get(phase, "")
            
            logger.info(f"🧠 Using RL strategy: {rl_action} in {phase} phase")
        
        # Generate response using agent (with RL strategy if available)
        response = await session.agent.generate_response(
            scammer_message=scammer_message,
            conversation_history=conversation_history,
            additional_context=rl_strategy_prompt,  # Pass RL strategy with phase
            scam_type=session.scam_type
        )
        
        # CRITICAL: Strip ALL emojis from response (LLM sometimes generates despite ban)
        # Unicode emoji ranges: https://unicode.org/emoji/charts/full-emoji-list.html
        import regex as re_emoji
        try:
            # Try using regex library for better emoji detection
            emoji_pattern = re_emoji.compile(r'\p{Emoji}', re_emoji.UNICODE)
            response = emoji_pattern.sub('', response).strip()
        except:
            # Fallback: strip common emojis manually
            common_emojis = ['🙏', '😭', '😊', '😟', '😢', '😔', '😳', '🤔', '😅', '😰', '😨', '😱']
            for emoji in common_emojis:
                response = response.replace(emoji, '')
            response = response.strip()
        
        logger.info(f"✅ Final response (emoji-stripped): {response}")
        
        return response
    
    def get_agent_notes(self, session: Session) -> str:
        """Get agent's observation notes."""
        if session.agent is None:
            return "No agent engaged yet"
        
        return session.agent.get_agent_notes()


# Global orchestrator instance
agent_orchestrator = AgentOrchestrator()
