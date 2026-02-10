"""State encoder for reinforcement learning."""
import json
from typing import Dict, Any, List
from app.models import Intelligence


class StateEncoder:
    """Encodes conversation state for RL agent."""
    
    @staticmethod
    def encode_state(
        scam_type: str,
        turn_number: int,
        intelligence_count: int,
        last_scammer_message: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Encode conversation state as JSON string.
        
        Args:
            scam_type: Type of scam detected
            turn_number: Current conversation turn
            intelligence_count: Number of intelligence items extracted
            last_scammer_message: Most recent scammer message
            conversation_history: Recent conversation messages
            
        Returns:
            JSON string representing state
        """
        # Calculate trust level based on conversation
        trust_level = StateEncoder._calculate_trust_level(conversation_history)
        
        # Detect urgency in scammer message
        urgency_level = StateEncoder._detect_urgency(last_scammer_message)
        
        state = {
            "scam_type": scam_type,
            "turn_number": turn_number,
            "intelligence_count": intelligence_count,
            "trust_level": trust_level,
            "urgency_level": urgency_level,
            "message_length": len(last_scammer_message.split()),
            "conversation_length": len(conversation_history)
        }
        
        return json.dumps(state)
    
    @staticmethod
    def decode_state(state_json: str) -> Dict[str, Any]:
        """Decode state from JSON string."""
        return json.loads(state_json)
    
    @staticmethod
    def _calculate_trust_level(conversation_history: List[Dict]) -> float:
        """
        Calculate how much scammer seems to trust the victim.
        
        Higher trust = scammer is more engaged and revealing.
        Range: 0.0 to 1.0
        """
        if not conversation_history:
            return 0.5
        
        # Simple heuristic: if scammer keeps talking, trust is increasing
        scammer_messages = [msg for msg in conversation_history if msg.get('sender') == 'scammer']
        
        if len(scammer_messages) == 0:
            return 0.5
        
        # More messages = more trust
        base_trust = min(len(scammer_messages) / 10, 1.0)
        
        # Check if scammer is asking for sensitive info (high trust)
        last_message = scammer_messages[-1].get('text', '').lower()
        sensitive_asks = ['cvv', 'password', 'pin', 'otp', 'bank account']
        
        if any(ask in last_message for ask in sensitive_asks):
            base_trust = min(base_trust + 0.3, 1.0)
        
        return base_trust
    
    @staticmethod
    def _detect_urgency(message: str) -> float:
        """
        Detect urgency level in scammer's message.
        
        Range: 0.0 (no urgency) to 1.0 (high urgency)
        """
        message_lower = message.lower()
        
        urgency_words = [
            'urgent', 'immediately', 'now', 'today', 'hurry',
            'quick', 'fast', 'within', 'expires', 'last chance'
        ]
        
        urgency_count = sum(1 for word in urgency_words if word in message_lower)
        
        # Normalize to 0-1
        return min(urgency_count / 3, 1.0)
    
    @staticmethod
    def state_to_vector(state_json: str) -> List[float]:
        """
        Convert state to numerical vector for neural network RL.
        
        This is useful for Deep Q-Learning (DQN).
        """
        state = StateEncoder.decode_state(state_json)
        
        # Encode scam_type as one-hot
        scam_types = ['bank_fraud', 'upi_fraud', 'phishing', 'investment', 
                      'job_offer', 'legal_threat', 'authority_impersonation', 'unknown']
        scam_type_encoding = [1.0 if state['scam_type'] == st else 0.0 for st in scam_types]
        
        # Numerical features (normalized to 0-1)
        vector = scam_type_encoding + [
            min(state['turn_number'] / 30, 1.0),  # Normalize turn number
            min(state['intelligence_count'] / 20, 1.0),  # Normalize intelligence count
            state['trust_level'],
            state['urgency_level'],
            min(state['message_length'] / 100, 1.0),  # Normalize message length
            min(state['conversation_length'] / 30, 1.0)  # Normalize conversation length
        ]
        
        return vector
