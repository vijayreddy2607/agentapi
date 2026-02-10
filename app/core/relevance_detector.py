"""
Relevance Detector - Determines if scammer message is relevant to ongoing conversation.
Prevents agent from responding to jokes, wrong numbers, gibberish, or conversation endings.
"""
import re
import logging
from typing import List, Tuple
from app.models import Message

logger = logging.getLogger(__name__)


class RelevanceDetector:
    """Detects if scammer message is relevant to the ongoing scam conversation."""
    
    # Scam-specific keywords for context validation
    SCAM_KEYWORDS = {
        "bank_fraud": ["account", "bank", "block", "kyc", "verify", "card", "atm", "pin"],
        "upi_fraud": ["upi", "payment", "gpay", "phonepe", "paytm", "money", "transaction", "refund"],
        "digital_arrest": ["police", "cbi", "ed", "arrest", "case", "court", "legal", "warrant", "investigation"],
        "job_offer": ["job", "salary", "work", "company", "hiring", "recruitment", "hr", "position"],
        "investment": ["invest", "profit", "trading", "stock", "crypto", "bitcoin", "returns", "scheme"],
        "loan": ["loan", "credit", "amount", "emi", "interest", "approved", "disbursement"],
        "phishing": ["link", "click", "verify", "update", "expire", "account", "otp"],
        "shopping": ["parcel", "delivery", "courier", "package", "order", "shipping", "cod"],
        "prize_lottery": ["won", "prize", "lottery", "winner", "claim", "congratulations"],
        "tax_refund": ["refund", "tax", "income", "return", "claim", "process"],
        "unknown": ["sir", "madam", "please", "urgent", "immediately", "now"]
    }
    
    # Patterns indicating scammer is ending/abandoning conversation
    ENDING_PATTERNS = [
        "ok bye", "goodbye", "talk later", "disconnect", "hang up",
        "don't waste my time", "you are useless", "forget it",
        "not interested", "leave me alone", "stop calling"
    ]
    
    # Patterns indicating scammer admits joke/mistake
    MISTAKE_PATTERNS = [
        "just kidding", "wrong number", "sorry mistake", "my bad",
        "nevermind", "forget it", "ignore", "oops", "wrong person",
        "lol", "haha", "prank"
    ]
    
    # Gibberish indicators
    GIBBERISH_PATTERNS = [
        r'^[a-z]{1,3}$',  # Single letters or very short
        r'^[A-Z\s]+$',    # All caps
        r'^\d+$',         # Only numbers
        r'^[^\w\s]+$'     # Only special characters
    ]
    
    @staticmethod
    def is_relevant(
        scammer_message: str,
        scam_type: str,
        conversation_history: List[Message],
        min_message_length: int = 5
    ) -> Tuple[bool, str, float]:
        """
        Check if scammer message is relevant to ongoing scam conversation.
        
        Args:
            scammer_message: Latest message from scammer
            scam_type: Type of scam detected
            conversation_history: Previous messages
            min_message_length: Minimum message length to consider
            
        Returns:
            Tuple of (is_relevant, reason, confidence_score)
            - is_relevant: True if message is relevant
            - reason: Explanation for decision
            - confidence_score: 0.0-1.0 confidence in relevance
        """
        message_lower = scammer_message.lower().strip()
        
        # Pattern 1: Scammer admits joke/mistake
        for pattern in RelevanceDetector.MISTAKE_PATTERNS:
            if pattern in message_lower:
                logger.info(f"Irrelevant: Scammer admitted '{pattern}'")
                return (False, "scammer_admitted_mistake", 0.95)
        
        # Pattern 2: Scammer ends conversation
        for pattern in RelevanceDetector.ENDING_PATTERNS:
            if pattern in message_lower:
                logger.info(f"Irrelevant: Scammer ending with '{pattern}'")
                return (False, "scammer_ending_conversation", 0.90)
        
        # Pattern 3: Gibberish detection
        if len(message_lower) < min_message_length:
            logger.info(f"Irrelevant: Message too short ({len(message_lower)} chars)")
            return (False, "message_too_short", 0.80)
        
        for gibberish_pattern in RelevanceDetector.GIBBERISH_PATTERNS:
            if re.match(gibberish_pattern, scammer_message.strip()):
                logger.info(f"Irrelevant: Gibberish pattern matched")
                return (False, "gibberish", 0.85)
        
        # Pattern 4: Topic shift detection (no scam keywords in recent context)
        if len(conversation_history) >= 2:
            # Get last 2 agent + scammer exchanges
            recent_msgs = conversation_history[-4:] if len(conversation_history) >= 4 else conversation_history
            recent_text = " ".join([m.text.lower() for m in recent_msgs])
            
            # Get keywords for this scam type
            keywords = RelevanceDetector.SCAM_KEYWORDS.get(scam_type, RelevanceDetector.SCAM_KEYWORDS["unknown"])
            
            # Check if recent context has scam keywords
            context_has_keywords = any(kw in recent_text for kw in keywords)
            message_has_keywords = any(kw in message_lower for kw in keywords)
            
            # If neither recent context nor current message has keywords, likely off-topic
            if not context_has_keywords and not message_has_keywords:
                logger.info(f"Irrelevant: Topic shifted (no scam keywords in recent context)")
                return (False, "topic_shifted", 0.70)
        
        # Pattern 5: Single word responses (often indicates frustration/disengagement)
        words = scammer_message.strip().split()
        if len(words) <= 2 and len(conversation_history) > 3:
            # Exception: Common scam words like "yes", "ok", "wait" are still relevant
            if message_lower not in ["yes", "ok", "okay", "wait", "no", "why", "what", "how"]:
                logger.info(f"Irrelevant: Single word response '{message_lower}' after multiple turns")
                return (False, "disengaged_single_word", 0.60)
        
        # Message appears relevant
        logger.info(f"Relevant: Message passes all checks")
        return (True, "relevant", 0.90)
    
    @staticmethod
    def get_graceful_ending(scam_type: str, reason: str) -> str:
        """
        Get a natural human-like ending response based on scam type and reason.
        
        Args:
            scam_type: Type of scam
            reason: Reason for ending (from is_relevant)
            
        Returns:
            Graceful ending message
        """
        # Different endings based on scam type and persona
        endings_by_type = {
            "bank_fraud": [
                "Ok sir, thank you",
                "Thik hai ji",
                "Okay, I will check later"
            ],
            "upi_fraud": [
                "Ok sir",
                "Thik hai, thank you",
                "Alright"
            ],
            "digital_arrest": [
                "Ok sir, understood",
                "Thank you sir",
                "Alright"
            ],
            "job_offer": [
                "Ok, I will think about it",
                "Thik hai bro",
                "Alright, thanks"
            ],
            "investment": [
                "Ok, let me think",
                "I'll check and get back",
                "Alright"
            ]
        }
        
        # Reason-specific endings
        if reason == "scammer_ending_conversation":
            return "Ok bye"
        elif reason == "scammer_admitted_mistake":
            return "Oh ok, no problem"
        elif reason == "gibberish":
            return "Sorry?"
        
        # Default: polite ending based on scam type
        endings = endings_by_type.get(scam_type, ["Ok", "Thik hai", "Alright"])
        
        import random
        return random.choice(endings)


# Singleton instance
relevance_detector = RelevanceDetector()
