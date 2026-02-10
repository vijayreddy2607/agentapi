"""Reward calculator for reinforcement learning."""
from typing import Dict, Any
from app.models import Intelligence
import logging

logger = logging.getLogger(__name__)


class RewardCalculator:
    """Calculate rewards for RL agent based on session outcomes."""
    
    # Reward weights
    INTELLIGENCE_REWARD = 10.0  # Per intelligence item
    CONVERSATION_TURN_REWARD = 1.0  # Per turn
    SCAMMER_CONFIDENCE_REWARD = 15.0  # NEW: If scammer feels in control
    SCAMMER_FRUSTRATION_PENALTY = -10.0  # NEW: Penalty if scammer frustrated (opposite of feeling in control)
    COMPLETION_REWARD = 50.0  # Session completed with good intel
    TIME_PENALTY = -0.01  # Small penalty for very long responses
    
    @classmethod
    def calculate_reward(
        cls,
        intelligence_extracted: int,
        conversation_turns: int,
        scammer_message: str,
        session_completed: bool = False,
        intelligence_threshold: int = 5
    ) -> float:
        """
        Calculate reward for current action.
        
        OPTIMIZATION GOAL: Make scammer feel IN CONTROL while extracting intelligence.
        - High reward if scammer sounds confident/excited (thinks victim is convinced)
        - Penalty if scammer sounds frustrated/suspicious (might abandon)
        
        Args:
            intelligence_extracted: Number of new intelligence items this turn
            conversation_turns: Total turns in conversation
            scammer_message: Latest scammer message (to detect confidence/frustration)
            session_completed: Whether session completed successfully
            intelligence_threshold: Min intelligence for completion bonus
            
        Returns:
            Reward value (can be negative)
        """
        reward = 0.0
        
        # 1. Intelligence extraction reward (main objective)
        reward += intelligence_extracted * cls.INTELLIGENCE_REWARD
        
        # 2. Conversation engagement reward
        reward += cls.CONVERSATION_TURN_REWARD
        
        # 3. NEW: Scammer confidence detection (BIG BONUS - scammer feels in control!)
        confidence_score = cls._detect_scammer_confidence(scammer_message)
        if confidence_score >= 0.7:  # High confidence (0.7-1.0)
            reward += cls.SCAMMER_CONFIDENCE_REWARD
            logger.info(f"✅ Scammer CONFIDENT (score={confidence_score:.2f})! +{cls.SCAMMER_CONFIDENCE_REWARD} reward")
        
        # 4. NEW: Scammer frustration detection (PENALTY - scammer might abandon!)
        if cls._detect_frustration(scammer_message):
            reward += cls.SCAMMER_FRUSTRATION_PENALTY
            logger.warning(f"⚠️ Scammer FRUSTRATED! {cls.SCAMMER_FRUSTRATION_PENALTY} penalty")
        
        # 5. Session completion bonus
        if session_completed and intelligence_extracted >= intelligence_threshold:
            reward += cls.COMPLETION_REWARD
            logger.info(f"Session completed successfully! +{cls.COMPLETION_REWARD} reward")
        
        # 6. Small time penalty for very long conversations with no progress
        if conversation_turns > 20 and intelligence_extracted == 0:
            reward += cls.TIME_PENALTY * (conversation_turns - 20)
        
        logger.debug(f"Calculated reward: {reward:.2f}")
        return reward
    
    @staticmethod
    def _detect_scammer_confidence(message: str) -> float:
        """
        NEW: Detect scammer confidence level (0.0-1.0).
        
        HIGH CONFIDENCE (0.7-1.0) - Scammer thinks victim is convinced:
        - Eager/pushy: "yes yes just do it", "very easy", "only 5 minutes"
        - Reassuring: "trust me", "don't worry", "safe process"
        - Giving detailed instructions (thinks victim will comply)
        
        MEDIUM (0.4-0.6) - Neutral:
        - Normal explanations
        - Answering questions
        
        LOW (0.0-0.3) - Scammer suspicious/frustrated:
        - Many questions: "why you asking so much?"
        - Short responses: "ok", "what?"
        - Threats escalating
        """
        message_lower = message.lower()
        
        # High confidence indicators
        high_confidence_phrases = [
            'yes yes', 'very easy', 'simple process', 'trust me',
            'don\'t worry', 'no problem', 'safe', 'guaranteed',
            'just do', 'only take', 'quick', 'fast', 'easy way',
            'i will help', 'let me show', 'step by step'
        ]
        
        # Low confidence / suspicious indicators  
        low_confidence_phrases = [
            'why you', 'are you going to', 'decide fast', 'yes or no',
            'stop asking', 'too many questions', 'don\'t waste'
        ]
        
        # Count matches
        high_matches = sum(1 for phrase in high_confidence_phrases if phrase in message_lower)
        low_matches = sum(1 for phrase in low_confidence_phrases if phrase in message_lower)
        
        # Long detailed messages = confident scammer
        message_length = len(message.split())
        
        # Calculate score
        if high_matches >= 2 or message_length > 30:
            return 0.9  # Very confident
        elif high_matches == 1:
            return 0.7  # Confident
        elif low_matches >= 1:
            return 0.2  # Suspicious/frustrated
        elif message_length < 5:
            return 0.3  # Short response = losing interest
        else:
            return 0.5  # Neutral
    
    @staticmethod
    def _detect_frustration(message: str) -> bool:
        """
        Detect if scammer is getting frustrated (PENALTY trigger).
        
        Frustration indicators:
        - Repetition
        - Anger/threats
        - Giving up language
        - Excessive questioning of victim
        """
        message_lower = message.lower()
        
        frustration_indicators = [
            # Repetition/urgency escalation
            'i told you', 'i said', 'listen', 'are you listening',
            
            # Anger
            'why you', 'what is your problem', 'stupid', 'idiot',
            
            # Giving up
            'forget it', 'never mind', 'waste of time', 'goodbye',
            
            # Increased threats
            'police will come', 'you will be arrested', 'your fault',
            
            # NEW: Impatience
            'how long', 'hurry up', 'decide now', 'last chance'
        ]
        
        return any(indicator in message_lower for indicator in frustration_indicators)
    
    @classmethod
    def calculate_session_success_score(
        cls,
        total_intelligence: int,
        total_turns: int,
        engagement_duration: int,
        scam_confirmed: bool
    ) -> float:
        """
        Calculate overall success score for a session (0-100).
        
        This is used for analytics and comparison.
        
        Args:
            total_intelligence: Total intelligence items extracted
            total_turns: Total conversation turns
            engagement_duration: Duration in seconds
            scam_confirmed: Whether scam was actually confirmed
            
        Returns:
            Success score (0-100)
        """
        score = 0.0
        
        # Intelligence component (40 points max)
        score += min(total_intelligence * 4, 40)
        
        # Engagement component (30 points max)
        score += min(total_turns * 1, 30)
        
        # Duration component (20 points max)
        score += min(engagement_duration / 30, 20)  # 10 min = 20 points
        
        # Confirmation bonus (10 points)
        if scam_confirmed:
            score += 10
        
        return min(score, 100.0)
