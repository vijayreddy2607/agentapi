"""Enhanced session management with database persistence and RL integration."""
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.models import Intelligence, Message
from app.agents import BaseAgent
from app.db import SessionModel, MessageModel, IntelligenceModel, RLTrainingDataModel, SessionLocal
from app.rl import RLAgent, RewardCalculator, StateEncoder
import logging
import json

logger = logging.getLogger(__name__)


class Session:
    """Represents a conversation session with database persistence."""
    
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
        
        # RL integration
        self.previous_intelligence_count = 0
        self.current_rl_action = None
    
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


class EnhancedSessionManager:
    """Enhanced session manager with database persistence and RL."""
    
    def __init__(self, enable_rl: bool = True):
        """
        Initialize enhanced session manager.
        
        Args:
            enable_rl: Whether to use RL for response selection
        """
        self.sessions: Dict[str, Session] = {}
        self.enable_rl = enable_rl
        
        if enable_rl:
            self.rl_agent = RLAgent()
            logger.info("RL agent enabled")
        else:
            self.rl_agent = None
            logger.info("RL agent disabled")
    
    def get_or_create_session(self, session_id: str) -> Session:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            logger.info(f"Creating new session: {session_id}")
            self.sessions[session_id] = Session(session_id)
        return self.sessions[session_id]
    
    def save_session_to_db(self, session: Session):
        """Save session to database."""
        db = SessionLocal()
        try:
            # Check if session exists
            db_session = db.query(SessionModel).filter_by(session_id=session.session_id).first()
            
            if db_session is None:
                # Create new
                db_session = SessionModel(
                    session_id=session.session_id,
                    scam_detected=session.scam_detected,
                    scam_type=session.scam_type,
                    agent_type=session.agent_type,
                    start_time=session.start_time,
                    total_messages=session.total_messages,
                    intelligence_count=session.intelligence.count_items(),
                    engagement_duration=session.get_engagement_duration(),
                    is_complete=session.is_complete
                )
                db.add(db_session)
            else:
                # Update existing
                db_session.total_messages = session.total_messages
                db_session.intelligence_count = session.intelligence.count_items()
                db_session.engagement_duration = session.get_engagement_duration()
                db_session.is_complete = session.is_complete
                
                if session.is_complete:
                    db_session.end_time = datetime.now()
                    # Calculate success score
                    db_session.success_score = RewardCalculator.calculate_session_success_score(
                        total_intelligence=session.intelligence.count_items(),
                        total_turns=session.total_messages,
                        engagement_duration=session.get_engagement_duration(),
                        scam_confirmed=session.scam_detected
                    )
            
            # Save messages (only new ones)
            existing_msg_count = db.query(MessageModel).filter_by(session_id=session.session_id).count()
            new_messages = session.conversation_history[existing_msg_count:]
            
            for msg in new_messages:
                # Handle timestamp - could be string or datetime
                if isinstance(msg.timestamp, str):
                    ts = datetime.fromisoformat(msg.timestamp.replace('Z', '+00:00'))
                else:
                    ts = msg.timestamp if isinstance(msg.timestamp, datetime) else datetime.now()
                
                db_message = MessageModel(
                    session_id=session.session_id,
                    sender=msg.sender,
                    text=msg.text,
                    timestamp=ts
                )
                db.add(db_message)
            
            # Save intelligence
            for upi in session.intelligence.upiIds:
                db.add(IntelligenceModel(
                    session_id=session.session_id,
                    type="upi",
                    value=upi
                ))
            
            for phone in session.intelligence.phoneNumbers:
                db.add(IntelligenceModel(
                    session_id=session.session_id,
                    type="phone",
                    value=phone
                ))
            
            for url in session.intelligence.phishingLinks:
                db.add(IntelligenceModel(
                    session_id=session.session_id,
                    type="url",
                    value=url
                ))
            
            for account in session.intelligence.bankAccounts:
                db.add(IntelligenceModel(
                    session_id=session.session_id,
                    type="bank_account",
                    value=account
                ))
            
            db.commit()
            logger.info(f"Saved session {session.session_id} to database")
            
        except Exception as e:
            logger.error(f"Failed to save session to database: {e}")
            db.rollback()
        finally:
            db.close()
    
    def get_rl_action(self, session: Session, scammer_message: str) -> Optional[str]:
        """
        Get RL agent's recommended action.
        
        Args:
            session: Current session
            scammer_message: Latest scammer message
            
        Returns:
            Action name or None if RL disabled
        """
        if not self.enable_rl or self.rl_agent is None:
            return None
        
        # Encode current state
        state = StateEncoder.encode_state(
            scam_type=session.scam_type,
            turn_number=session.total_messages,
            intelligence_count=session.intelligence.count_items(),
            last_scammer_message=scammer_message,
            conversation_history=[msg.__dict__ for msg in session.conversation_history]
        )
        
        # Select action
        action = self.rl_agent.select_action(state, explore=True)
        
        # Store state for later update
        session.current_rl_action = action
        
        logger.info(f"RL selected action: {action}")
        return action
    
    def update_rl(self, session: Session, new_intelligence_count: int, scammer_message: str):
        """
        Update RL agent with reward after action.
        
        Args:
            session: Current session
            new_intelligence_count: Intelligence count after agent response
            scammer_message: Latest scammer message (for frustration detection)
        """
        if not self.enable_rl or self.rl_agent is None or session.current_rl_action is None:
            return
        
        # Calculate reward
        intelligence_extracted = new_intelligence_count - session.previous_intelligence_count
        reward = RewardCalculator.calculate_reward(
            intelligence_extracted=intelligence_extracted,
            conversation_turns=session.total_messages,
            scammer_message=scammer_message,
            session_completed=session.is_complete
        )
        
        # Encode next state
        next_state = StateEncoder.encode_state(
            scam_type=session.scam_type,
            turn_number=session.total_messages,
            intelligence_count=new_intelligence_count,
            last_scammer_message=scammer_message,
            conversation_history=[msg.__dict__ for msg in session.conversation_history]
        )
        
        # Get previous state (reconstruct from session)
        prev_state = StateEncoder.encode_state(
            scam_type=session.scam_type,
            turn_number=session.total_messages - 1,
            intelligence_count=session.previous_intelligence_count,
            last_scammer_message=scammer_message,
            conversation_history=[msg.__dict__ for msg in session.conversation_history[:-1]]
        )
        
        # Update Q-table
        self.rl_agent.update(
            state=prev_state,
            action=session.current_rl_action,
            reward=reward,
            next_state=next_state
        )
        
        # Save RL training data to database
        self._save_rl_training_data(session, prev_state, session.current_rl_action, reward, next_state)
        
        # Update previous intelligence count
        session.previous_intelligence_count = new_intelligence_count
        
        logger.info(f"RL updated with reward: {reward:.2f}")
    
    def _save_rl_training_data(
        self,
        session: Session,
        state: str,
        action: str,
        reward: float,
        next_state: str
    ):
        """Save RL training data to database."""
        db = SessionLocal()
        try:
            rl_data = RLTrainingDataModel(
                session_id=session.session_id,
                turn_number=session.total_messages,
                state=state,
                action=action,
                reward=reward,
                next_state=next_state
            )
            db.add(rl_data)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save RL training data: {e}")
            db.rollback()
        finally:
            db.close()
    
    def mark_complete(self, session_id: str):
        """Mark session as complete and save to database."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.is_complete = True
            self.save_session_to_db(session)
            
            # Save RL model periodically
            if self.enable_rl and self.rl_agent:
                self.rl_agent.save_model()
            
            logger.info(f"Session {session_id} marked complete and saved")
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get existing session."""
        return self.sessions.get(session_id)
    
    def cleanup_old_sessions(self, max_age_seconds: int = 3600):
        """Remove old sessions from memory (they're saved in DB)."""
        current_time = datetime.now()
        to_remove = []
        
        for session_id, session in self.sessions.items():
            age = (current_time - session.start_time).total_seconds()
            if age > max_age_seconds:
                # Save before removing
                self.save_session_to_db(session)
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.sessions[session_id]
            logger.info(f"Cleaned up old session: {session_id}")
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return len([s for s in self.sessions.values() if not s.is_complete])


# Global enhanced session manager instance
session_manager = EnhancedSessionManager(enable_rl=True)
