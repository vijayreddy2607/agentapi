"""Q-Learning Reinforcement Learning Agent."""
import json
import pickle
import os
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import random
import logging

logger = logging.getLogger(__name__)


class RLAgent:
    """Q-Learning agent for optimizing honeypot responses."""
    
    # Define possible actions (expanded for better engagement)
    ACTIONS = [
        # Original 5 actions
        "ask_clarifying_question",  # Ask about details to extract info
        "show_compliance",           # Appear willing to comply
        "create_obstacle",           # Create believable problem
        "express_confusion",         # Play dumb about technical terms
        "ask_for_proof",            # Request verification/credentials
        
        # NEW: 5 additional actions for multi-turn engagement
        "share_fake_details",        # Share fake info to get scammer's real details
        "express_fear",              # Show panic/worry to encourage more details
        "request_time",              # Ask for delay to keep conversation going
        "feign_technical_issue",     # Pretend tech problems to stall
        "ask_for_supervisor"         # Request to speak with manager/senior
    ]
    
    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        exploration_rate: float = 0.2,
        model_path: str = "rl_model.pkl"
    ):
        """
        Initialize Q-Learning agent.
        
        Args:
            learning_rate: How much to update Q-values (alpha)
            discount_factor: How much to value future rewards (gamma)
            exploration_rate: Probability of random action (epsilon)
            model_path: Path to save/load model
        """
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.model_path = model_path
        
        # Q-table: Q[state][action] = expected_reward
        self.q_table: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {action: 0.0 for action in self.ACTIONS}
        )
        
        # Load existing model if available
        self.load_model()
        
        logger.info(f"RL Agent initialized with {len(self.q_table)} states")
    
    def select_action(self, state: str, explore: bool = True) -> str:
        """
        Select best action for given state using epsilon-greedy policy.
        
        Args:
            state: JSON string representing current state
            explore: Whether to use exploration (training mode)
            
        Returns:
            Selected action name
        """
        # Exploration: random action
        if explore and random.random() < self.exploration_rate:
            action = random.choice(self.ACTIONS)
            logger.debug(f"Exploring: selected random action '{action}'")
            return action
        
        # Exploitation: best action based on Q-values
        q_values = self.q_table[state]
        best_action = max(q_values, key=q_values.get)
        logger.debug(f"Exploiting: selected best action '{best_action}' (Q={q_values[best_action]:.2f})")
        
        return best_action
    
    def update(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str
    ):
        """
        Update Q-value using Q-learning update rule.
        
        Q(s,a) = Q(s,a) + α[r + γ * max(Q(s',a')) - Q(s,a)]
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state after action
        """
        current_q = self.q_table[state][action]
        
        # Max Q-value for next state
        next_max_q = max(self.q_table[next_state].values()) if next_state else 0.0
        
        # Q-learning update
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * next_max_q - current_q
        )
        
        self.q_table[state][action] = new_q
        
        logger.debug(
            f"Updated Q({action}): {current_q:.2f} → {new_q:.2f} "
            f"(reward={reward:.2f})"
        )
    
    def save_model(self):
        """Save Q-table to disk."""
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(dict(self.q_table), f)
            logger.info(f"RL model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to save RL model: {e}")
    
    def load_model(self):
        """Load Q-table from disk."""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    loaded_q_table = pickle.load(f)
                
                # Convert to defaultdict
                self.q_table = defaultdict(
                    lambda: {action: 0.0 for action in self.ACTIONS},
                    loaded_q_table
                )
                
                logger.info(f"RL model loaded from {self.model_path} ({len(self.q_table)} states)")
            except Exception as e:
                logger.error(f"Failed to load RL model: {e}")
        else:
            logger.info("No existing RL model found, starting fresh")
    
    def get_action_prompt(self, action: str, scam_type: str) -> str:
        """
        Get prompt modifier based on RL action and scam type.
        
        Args:
            action: Selected action name
            scam_type: Type of scam detected
            
        Returns:
            Prompt addition to guide agent behavior
        """
        # Context-aware examples based on scam type
        context_examples = {
            "ask_clarifying_question": {
                "bank_fraud": "Which bank department are you from? What is your employee ID?",
                "upi_fraud": "Which payment app is this? Can you give me your company registration number?",
                "phishing": "Which website is this? Can you send me the link in SMS so I can check?",
                "investment": "Which company are you from? Do you have SEBI registration?",
                "job_offer": "Which company is hiring? Can I see the job posting online?",
                "legal_threat": "Which court is this from? What is the case number?",
                "authority_impersonation": "Can I have your badge number? Which office are you calling from?",
                "unknown": "Can you tell me more details? How did you get my number?"
            },
            "ask_for_proof": {
                "bank_fraud": "Can I call you back on the bank's official number? What is your employee ID?",
                "upi_fraud": "Can you send me confirmation from the payment app? What's your support ticket number?",
                "phishing": "Can you send me an official email? What is your company domain?",
                "investment": "Do you have company registration? Can I verify this with SEBI?",
                "job_offer": "Can I see the job posting on your company website? What's the HR manager's name?",
                "legal_threat": "Can I verify this with the court? What is your officer ID?",
                "authority_impersonation": "Can I call your office to verify? What is your supervisor's name?",
                "unknown": "How can I verify you are genuine? Can you provide some proof?"
            }
        }
        
        prompts = {
            "ask_clarifying_question": f"""
STRATEGY: Ask clarifying questions to extract information.
Example for this scam type: {context_examples["ask_clarifying_question"].get(scam_type, context_examples["ask_clarifying_question"]["unknown"])}
""",
            "show_compliance": """
STRATEGY: Show willingness to comply but add small delays.
Examples:
- "Okay beta, let me find that information..."
- "Yes, I will do. Just give me one minute..."
- "Thik hai, I am ready. What should I do?"
- "Alright, let me get my things first..."
""",
            "create_obstacle": """
STRATEGY: Create realistic obstacles that require scammer to help/wait.
Examples:
- "My things are upstairs, wife is sleeping. Can you wait?"
- "Internet is very slow today, app is not loading..."
- "I forgot my reading glasses, can't see clearly..."
- "Phone battery is low, might switch off..."
""",
            "express_confusion": """
STRATEGY: Play dumb about technical terms to make scammer explain.
Examples:
- "What is this beta? I don't understand..."
- "I'm not very good with technology, can you explain?"
- "I don't know how to do this properly..."
- "Which button to click? I am not understanding..."
""",
            "ask_for_proof": f"""
STRATEGY: Request verification to extract scammer's fake credentials.
Example for this scam type: {context_examples["ask_for_proof"].get(scam_type, context_examples["ask_for_proof"]["unknown"])}
""",
            # NEW ACTION PROMPTS
            "share_fake_details": """
STRATEGY: Share fake information to build trust and extract scammer's real details.
Examples:
- "My UPI ID is ramesh123@paytm. What is yours?"
- "My account number is 1234567890. Where should I transfer?"
- "I can send ₹100 first. What is your number?"
- "My PAN is ABCDE1234F. What documents do you need?"
""",
            "express_fear": """
STRATEGY: Show panic and worry to make scammer reveal more about consequences/threats.
Examples:
- "Oh no! What will happen if I don't do this? Will I go to jail?"
- "I'm so scared! How much trouble am I in?"
- "This is terrible! Will my family be affected too?"
- "Please help me! I don't want any problems!"
""",
            "request_time": """
STRATEGY: Ask for delay to keep conversation going and extract more details.
Examples:
- "Can this wait until tomorrow? My son will help me."
- "I'm at work right now. Can you call back in evening?"
- "Can we do this after lunch? I need to eat first."
- "Give me 30 minutes please. I need to arrange things."
""",
            "feign_technical_issue": """
STRATEGY: Pretend to have technical problems to waste scammer's time.
Examples:
- "My phone is hanging. Apps are not working properly."
- "Internet is very slow.  Loading... loading... not opening."
- "I can't find the app. Where is it on my phone?"
- "Screen went black. Wait, let me restart..."
""",
            "ask_for_supervisor": """
STRATEGY: Request to speak with senior person to extract more details.
Examples:
- "Can I speak to your manager? This sounds serious."
- "Is there a supervisor I can talk to? I don't understand you."
- "Let me speak to senior officer please."
- "Can your boss call me? I want to confirm with someone higher."
"""
        }
        
        return prompts.get(action, "")
    
    def get_stats(self) -> Dict:
        """Get training statistics."""
        total_states = len(self.q_table)
        
        # Find most visited states
        avg_q_values = {
            state: sum(actions.values()) / len(actions)
            for state, actions in self.q_table.items()
        }
        
        return {
            "total_states": total_states,
            "total_actions": len(self.ACTIONS),
            "exploration_rate": self.exploration_rate,
            "learning_rate": self.learning_rate,
            "avg_q_value": sum(avg_q_values.values()) / len(avg_q_values) if avg_q_values else 0.0
        }


# Global RL agent instance
rl_agent = RLAgent()
