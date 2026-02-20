"""Agent orchestrator — multi-agent pipeline coordinator."""
import asyncio
import logging
from typing import Literal, Optional, List, Dict, Any
from app.agents import UncleAgent, WorriedAgent, TechSavvyAgent, AuntyAgent, StudentAgent, BaseAgent
from app.agents.intelligence_analyst_agent import intelligence_analyst
from app.agents.conversation_director_agent import conversation_director
from app.core.session_manager import Session, ScammerConversationState

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Multi-agent pipeline orchestrator.
    
    Pipeline per turn:
    1. IntelligenceAnalystAgent  — analyze scammer message (parallel)
    2. ConversationDirectorAgent — decide persona + strategy
    3. Persona Agent             — generate human-like response
    4. Attach INTELLIGENCE_LOG   — to session and response
    """

    def __init__(self):
        self.agent_pool = {
            "uncle": UncleAgent,
            "worried": WorriedAgent,
            "techsavvy": TechSavvyAgent,
            "aunty": AuntyAgent,
            "student": StudentAgent,
        }

    def get_agent(
        self,
        agent_type: Literal["uncle", "worried", "techsavvy", "aunty", "student"],
        session: Session
    ) -> BaseAgent:
        """Get or create agent for session."""
        if session.agent is not None:
            logger.info(f"Reusing existing {session.agent_type} agent for session {session.session_id}")
            return session.agent

        agent_class = self.agent_pool.get(agent_type, UncleAgent)
        agent = agent_class()
        session.agent = agent
        session.agent_type = agent_type
        logger.info(f"Created new {agent_type} agent for session {session.session_id}")
        return agent

    def _switch_agent(self, new_type: str, session: Session) -> BaseAgent:
        """Switch to a different persona agent mid-conversation."""
        agent_class = self.agent_pool.get(new_type, UncleAgent)
        agent = agent_class()
        session.agent = agent
        session.agent_type = new_type
        logger.info(f"[Director] Switched to {new_type} agent for session {session.session_id}")
        return agent

    def get_conversation_phase(self, turn_count: int) -> str:
        """Determine conversation phase based on turn count."""
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
        rl_action: str = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate agent response using the full multi-agent pipeline.
        
        Pipeline:
        1. Run IntelligenceAnalystAgent in parallel with setup
        2. Run ConversationDirectorAgent to decide strategy
        3. Optionally switch persona based on director decision
        4. Generate persona response with director context
        5. Return (response_text, intelligence_log)
        
        Args:
            session: Current session
            scammer_message: Latest scammer message
            conversation_history: Previous messages
            rl_action: RL-selected action strategy (optional)
            
        Returns:
            Tuple of (response_text, intelligence_log)
        """
        if session.agent is None:
            raise ValueError(f"No agent assigned to session {session.session_id}")

        turn_number = session.total_messages
        phase = self.get_conversation_phase(turn_number)
        logger.info(f"📊 Multi-agent pipeline: turn={turn_number}, phase={phase}")

        # ── STEP 1: Run IntelligenceAnalystAgent (fast, parallel-ready) ──────────
        intel_log = await intelligence_analyst.analyze(
            message=scammer_message,
            turn_number=turn_number,
            scam_type=session.scam_type,
            conversation_history=conversation_history
        )
        logger.info(f"[INTELLIGENCE_LOG] {intel_log}")

        # ── STEP 1b: Update ScammerConversationState from this turn ──────────────
        state: ScammerConversationState = session.scammer_state

        # Mark what scammer shared this turn (from intel_log)
        if intel_log.get("upi_ids"):
            state.mark_shared("upi_id")
        if intel_log.get("phone_numbers"):
            state.mark_shared("phone")
        if intel_log.get("emails"):
            state.mark_shared("email")
        if intel_log.get("urls") or intel_log.get("links"):
            state.mark_shared("url")
        if intel_log.get("bank_accounts"):
            state.mark_shared("bank_account")

        # Detect refusals in scammer message — mark specific field refused
        _refusal_phrases = [
            "cannot give", "can't give", "cant give", "cannot share",
            "not allowed", "should not give", "won't give", "wont give",
            "not supposed to", "security reasons", "confidential",
            "why do you need", "just proceed", "stop asking",
        ]
        scammer_lower = scammer_message.lower()
        if any(p in scammer_lower for p in _refusal_phrases):
            if any(w in scammer_lower for w in ["number", "phone", "mobile", "contact", "whatsapp"]):
                state.mark_refused("phone")
            elif any(w in scammer_lower for w in ["email", "mail"]):
                state.mark_refused("email")
            elif any(w in scammer_lower for w in ["upi", "link", "website", "url"]):
                state.mark_refused("url")
            logger.info(f"[State] Refusal detected. refused={state.refused_fields}")

        # Count pressure and suspicion signals
        if any(w in scammer_lower for w in ["urgent", "immediately", "block", "suspend", "hurry", "deadline"]):
            state.add_urgency()
            state.add_tactic("urgency")
        if any(w in scammer_lower for w in ["legal", "police", "court", "arrest", "warrant", "penalty"]):
            state.add_tactic("threat")
        if any(w in scammer_lower for w in ["rbi", "cbi", "government", "officer", "official"]):
            state.add_tactic("authority")
        if any(w in scammer_lower for w in ["bot", "ai", "automated", "robot", "fake", "not real"]):
            state.add_suspicion()

        logger.info(f"[State] shared={state.shared_fields}, refused={state.refused_fields}, urgency={state.urgency_count}, suspicion={state.suspicion_count}")

        # ── STEP 2: ConversationDirectorAgent decides strategy ──────────────────
        # Build accumulated intelligence dict from session
        accumulated_intel = {}
        if hasattr(session, 'intelligence') and session.intelligence:
            accumulated_intel = {
                "upi_ids": list(getattr(session.intelligence, 'upiIds', set())),
                "phone_numbers": list(getattr(session.intelligence, 'phoneNumbers', set())),
                "bank_accounts": list(getattr(session.intelligence, 'bankAccounts', set())),
                "urls": list(getattr(session.intelligence, 'phishingLinks', set())),
            }

        director_decision = conversation_director.decide(
            scam_type=session.scam_type or "unknown",
            turn_number=turn_number,
            current_persona=session.agent_type,
            intelligence_log=intel_log,
            conversation_history=conversation_history,
            accumulated_intelligence=accumulated_intel
        )

        # ── STEP 3: Switch persona if director recommends it ──────────────────────
        if director_decision.get("should_switch_persona"):
            new_persona = director_decision["persona"]
            if new_persona != session.agent_type:
                self._switch_agent(new_persona, session)

        # ── STEP 4: Build additional context for persona agent ────────────────────
        additional_context = director_decision.get("additional_context", "")

        # Inject ScammerConversationState summary — tells LLM what was shared/refused
        state_summary = session.scammer_state.summary()
        if state_summary:
            additional_context = f"CONVERSATION MEMORY:\n{state_summary}\n\n{additional_context}"

        # Add RL strategy if provided
        if rl_action:
            try:
                from app.rl import RLAgent
                rl_agent = RLAgent()
                rl_strategy = rl_agent.get_action_prompt(rl_action, session.scam_type)
                phase_guidance = {
                    "build_trust": "\n\nPHASE: Build Trust - Appear naive and interested.",
                    "extract_info": "\n\nPHASE: Extract Info - Ask questions to gather intelligence.",
                    "verify_details": "\n\nPHASE: Verify Details - Challenge the scammer.",
                    "stall_tactics": "\n\nPHASE: Stall Tactics - Waste time with obstacles.",
                }
                additional_context += f"\n\n{rl_strategy}{phase_guidance.get(phase, '')}"
                logger.info(f"🧠 RL strategy added: {rl_action}")
            except Exception as e:
                logger.warning(f"RL strategy failed: {e}")

        # ── STEP 5: Generate persona response ─────────────────────────────────────
        # Build an extracted_intel dict from session so the LLM knows what's already captured
        extracted_intel_dict = None
        if hasattr(session, 'intelligence') and session.intelligence:
            extracted_intel_dict = {
                "phoneNumbers":   list(getattr(session.intelligence, 'phoneNumbers', set())),
                "upiIds":         list(getattr(session.intelligence, 'upiIds', set())),
                "bankAccounts":   list(getattr(session.intelligence, 'bankAccounts', set())),
                "emailAddresses": list(getattr(session.intelligence, 'emailAddresses', set())),
                "phishingLinks":  list(getattr(session.intelligence, 'phishingLinks', set())),
                "caseIds":        list(getattr(session.intelligence, 'caseIds', set())),
            }

        response = await session.agent.generate_response(
            scammer_message=scammer_message,
            conversation_history=conversation_history,
            additional_context=additional_context,
            scam_type=session.scam_type,
            extracted_intel=extracted_intel_dict
        )

        response = response.strip()
        logger.info(f"✅ Multi-agent response (turn {turn_number}): {response[:80]}...")

        return response, intel_log

    def get_agent_notes(self, session: Session) -> str:
        """Get agent's observation notes."""
        if session.agent is None:
            return "No agent engaged yet"
        return session.agent.get_agent_notes()


# Global orchestrator instance
agent_orchestrator = AgentOrchestrator()
