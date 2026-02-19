"""Session management for tracking conversations."""
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from app.models import Intelligence, Message
from app.agents import BaseAgent
import logging

logger = logging.getLogger(__name__)


class ScammerConversationState:
    """
    Lightweight in-memory tracker for what we know about the scammer
    within the CURRENT conversation. Resets every session — no DB needed.

    Tracks:
    - refused_fields:   things scammer refused to share (don't ask again)
    - shared_fields:    things scammer already gave (don't re-ask)
    - urgency_count:    how many urgency/threat lines scammer used
    - suspicion_count:  how many times scammer seemed suspicious of us
    - tactics_seen:     set of tactic types scammer has used (urgency, threat, authority)
    """

    def __init__(self):
        self.refused_fields: Set[str] = set()       # e.g. {"phone", "email"}
        self.shared_fields: Set[str] = set()        # e.g. {"upi_id", "url", "phone"}
        self.urgency_count: int = 0                 # how many urgency lines used
        self.suspicion_count: int = 0               # how suspicious of us
        self.tactics_seen: Set[str] = set()         # urgency / threat / authority

    def mark_refused(self, field: str):
        """Scammer refused to share this field."""
        self.refused_fields.add(field.lower())

    def mark_shared(self, field: str):
        """Scammer shared this field — don't ask for it again."""
        self.shared_fields.add(field.lower())
        # If they shared it, remove from refused
        self.refused_fields.discard(field.lower())

    def add_urgency(self):
        self.urgency_count += 1

    def add_suspicion(self):
        self.suspicion_count += 1

    def add_tactic(self, tactic: str):
        self.tactics_seen.add(tactic.lower())

    def was_refused(self, field: str) -> bool:
        return field.lower() in self.refused_fields

    def was_shared(self, field: str) -> bool:
        return field.lower() in self.shared_fields

    @property
    def is_suspicious(self) -> bool:
        """True if scammer seems suspicious of the agent."""
        return self.suspicion_count >= 2

    @property
    def is_high_pressure(self) -> bool:
        """True if scammer is applying lots of urgency/threat pressure."""
        return self.urgency_count >= 3

    def safe_to_ask(self, field: str) -> bool:
        """Returns True if it's safe to ask for this field (not refused AND not already shared)."""
        return not self.was_refused(field) and not self.was_shared(field)

    def summary(self) -> str:
        """Human-readable state summary for injection into LLM context."""
        lines = []
        if self.shared_fields:
            lines.append(f"Scammer ALREADY GAVE: {', '.join(self.shared_fields)} — DO NOT ask again.")
        if self.refused_fields:
            lines.append(f"Scammer REFUSED to share: {', '.join(self.refused_fields)} — DO NOT ask again, pivot to something else.")
        if self.is_high_pressure:
            lines.append(f"Scammer used urgency/threats {self.urgency_count}x — they're getting aggressive. Show more hesitation.")
        if self.is_suspicious:
            lines.append(f"Scammer seems suspicious of you ({self.suspicion_count}x). Be more natural, less question-heavy.")
        if self.tactics_seen:
            lines.append(f"Tactics seen: {', '.join(self.tactics_seen)}")
        return "\n".join(lines) if lines else ""


class Session:
    """Represents a conversation session."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.scam_detected = False
        self.scam_type = "unknown"
        self.agent: Optional[BaseAgent] = None
        self.agent_type = ""
        self.conversation_history: list[Message] = []
        self.intelligence = Intelligence()
        self.start_time = datetime.now()
        self.total_messages = 0
        self.agent_messages = 0
        self.scammer_messages = 0
        self.is_complete = False
        # ── In-session scammer state tracker (no DB, resets per conversation) ──
        self.scammer_state = ScammerConversationState()
    
    def add_message(self, message: Message):
        """Add a message to conversation history."""
        self.conversation_history.append(message)
        self.total_messages += 1
        
        if message.sender == "scammer":
            self.scammer_messages += 1
        else:
            self.agent_messages += 1
    
    def get_engagement_duration(self) -> int:
        """Get engagement duration in seconds."""
        return int((datetime.now() - self.start_time).total_seconds())
    
    def should_complete(self, max_turns: int, timeout_seconds: int) -> bool:
        """Check if session should be marked complete."""
        # Max turns reached
        if self.total_messages >= max_turns:
            logger.info(f"Session {self.session_id} reached max turns")
            return True
        
        # Timeout (no new messages)
        duration = self.get_engagement_duration()
        if duration >= timeout_seconds:
            logger.info(f"Session {self.session_id} timed out")
            return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "sessionId": self.session_id,
            "scamDetected": self.scam_detected,
            "scamType": self.scam_type,
            "agentType": self.agent_type,
            "totalMessages": self.total_messages,
            "engagementDuration": self.get_engagement_duration(),
            "intelligenceCount": self.intelligence.count_items(),
            "isComplete": self.is_complete
        }


class SessionManager:
    """Manages all active and past sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
    
    def get_or_create_session(self, session_id: str) -> Session:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            logger.info(f"Creating new session: {session_id}")
            self.sessions[session_id] = Session(session_id)
        return self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get existing session."""
        return self.sessions.get(session_id)
    
    def mark_complete(self, session_id: str):
        """Mark session as complete."""
        if session_id in self.sessions:
            self.sessions[session_id].is_complete = True
            logger.info(f"Session {session_id} marked complete")
    
    def cleanup_old_sessions(self, max_age_seconds: int = 3600):
        """Remove sessions older than max_age_seconds."""
        current_time = datetime.now()
        to_remove = []
        
        for session_id, session in self.sessions.items():
            age = (current_time - session.start_time).total_seconds()
            if age > max_age_seconds:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.sessions[session_id]
            logger.info(f"Cleaned up old session: {session_id}")
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return len([s for s in self.sessions.values() if not s.is_complete])


# Global session manager instance
session_manager = SessionManager()
