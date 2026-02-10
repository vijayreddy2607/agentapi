"""Aunty agent - Gossipy, chatty middle-aged woman persona."""
from app.agents.base_agent import BaseAgent
from app.prompts.aunty_persona import AUNTY_SYSTEM_PROMPT, AUNTY_FEW_SHOT_EXAMPLES
import random


class AuntyAgent(BaseAgent):
    """Aunty persona - Gossipy, chatty, social character."""
    
    def __init__(self):
        super().__init__(persona_name="Sunita Aunty")
    
    def get_system_prompt(self) -> str:
        """Return Aunty's system prompt."""
        return AUNTY_SYSTEM_PROMPT
    
    def get_few_shot_examples(self) -> list:
        """Return Aunty's conversation examples."""
        return AUNTY_FEW_SHOT_EXAMPLES
    
    def _get_stateful_fallback(self, scammer_message: str, turn_count: int) -> str:
        """Aunty's stateful fallback responses."""
        # Use aunty-specific progression
        return self._get_aunty_stateful_fallback(turn_count)
    
    def _get_aunty_stateful_fallback(self, turn_count: int) -> str:
        """Aunty progression: friendly→chatty→story-telling→family-check→stall."""
        responses = [
            # Turn 0 (Very Friendly & Curious)
            [
                "Hayy! Really beta? That sounds nice! What is your good name? Where you calling from?",
                "Arre! This is so surprising! Tell me beta, which company is this? You sound so young!",
                "Oh my god! What happened? You tell me slowly, I am not understanding. What is your name?"
            ],
            # Turn 1 (Chatty & Personal)
            [
                "Achha achha! You are from Mumbai? Nice city! My sister lives there only. Are you married beta?",
                "Good good! But first tell me, where is your office? My daughter Priya also works in such company.",
                "Haan haan I am listening! But so hot today na? You had lunch? What you ate?"
            ],
            # Turn 2 (Gets Distracted)
            [
                "Okay okay! But wait, my serial is starting on TV. This is very important episode! You know 'Anupama'?",
                "Just one minute beta, my neighbor Sharma aunty is calling from balcony. HAANJI AUNTYJI! Sorry, what you were saying?",
                "Arre! Door bell ringing! Might be vegetable vendor. Wait two minutes, I come back quickly!"
            ],
            # Turn 3 (Shares Stories)
            [
                "You know what beta? Same thing happened with my kitty party friend! They said won prize but was all fake only!",
                "Hayy! This reminds me, my husband got similar call last month. He said these people are everywhere nowadays.",
                "Achha! My daughter was telling something about these calls. She said never give details on phone. You know na?"
            ],
            # Turn 4 (Asks for Verification)
            [
                "But beta, how I know this is real? My son Rohit said always ask for company registration number and all.",
                "Okay but what is your employee ID? My daughter said I should ask these things. Give me your supervisor name?",
                "Thik hai! Send me WhatsApp message with all details. I will show to my son-in-law, he is in police department."
            ],
            # Turn 5 (Family Intervention)
            [
                "Wait beta! My daughter just came home. PRIYA! Come here! Someone calling about prize. You talk to them!",
                "Arre my husband is saying don't do anything on phone! He is very strict about these things. You send email!",
                "Haan haan! But let me call my son first. He understands all this technical matters. You give your number?"
            ],
            # Turn 6 (Starts Doubting)
            [
                "Why you need my Aadhaar details beta? That is confidential na? My daughter will get angry if I give!",
                "Processing fee? But prize should be free na? My friend said if they ask money, it is suspicious!",
                "So many questions you are asking! What is your office address? I will come there personally with my daughter."
            ],
            # Turn 7 (Creates Obstacles)
            [
                "Beta I need to discuss with family. This is big matter! You call tomorrow after 12, I will confirm!",
                "My daughter is saying no no don't give any details! She is very smart, working in TCS company. She knows everything!",
                "Wait wait! My daal is burning in kitchen! I come back in 15 minutes! Don't disconnect!"
            ],
            # Turn 8 (More Delays)
            [
                "Arre beta, my head is paining! I take medicine and rest. You call evening time, we talk properly!",
                "Actually I am going to temple now. Ganesh Chaturthi puja is there. Cannot talk about money matters now!",
                "Let me think beta! My BP goes up when tension comes. I need to lie down little bit!"
            ],
            # Turn 9+ (Maximum Stalling)
            [
                "Beta you sound nice but my husband is very suspicious person! He said put phone down! Very strict he is!",
                "Hayy! So much confusion! I am simple housewife, don't understand all this! My children handle everything!",
                "Achha beta, you seem good person! But nowadays so many frauds happening! Let me verify first thoroughly!"
            ],
        ]
        
        # Select options for current turn (cap at max length)
        idx = min(turn_count, len(responses) - 1)
        options = responses[idx]
        return random.choice(options)
