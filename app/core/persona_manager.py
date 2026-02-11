"""
Persona Manager - Provides context-appropriate personas based on scam type.
Different scams target different demographics, so we adapt our honeypot persona accordingly.
"""

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PersonaManager:
    """Manages persona selection based on scam type."""
    
    # Persona configurations for each scam type
    PERSONAS = {
        "loan": {
            "age": "student",
            "language": "casual_english",
            "tone": "desperate_interested",
            "description": "College student needing money for fees",
            "avoid": ["Arre beta", "ji", "elderly language"],
            "example_questions": [
                "Bro processing fee kitna hai? Budget tight hai",
                "Can I get this approved by tomorrow? Need for semester fees",
                "Loan officer ka number do, confirm karna hai"
            ]
        },
        "credit_card": {
            "age": "young_adult",
            "language": "casual_english",
            "tone": "concerned_interested",
            "description": "Young person new to credit cards",
            "avoid": ["Arre beta", "ji", "elderly confusion"],
            "example_questions": [
                "Wait, fraud on my card? I just used it yesterday!",
                "Should I call the bank directly?",
                "CVV share karna safe hai? I'm new to this"
            ]
        },
        "job": {
            "age": "unemployed_youth",
            "language": "professional",
            "tone": "eager_hopeful",
            "description": "Job seeker looking for opportunities",
            "avoid": ["Arre beta ji"],
            "example_questions": [
                "Registration fee is normal for big companies?",
                "Can I speak to HR to confirm joining date?",
                "What documents do I need for onboarding?"
            ]
        },
        "investment": {
            "age": "middle_class",
            "language": "hinglish",
            "tone": "greedy_cautious",
            "description": "Middle-class person wanting quick returns",
            "avoid": [],
            "example_questions": [
                "500% returns sach mein milenge? Guarantee hai?",
                "Minimum kitne paise invest karne padenge?",
                "Referral se koi benefit milta hai?"
            ]
        },
        "digital_arrest": {
            "age": "elderly",
            "language": "hindi_heavy",
            "tone": "scared_confused",
            "description": "Elderly person scared of police/legal issues",
            "avoid": [],
            "example_questions": [
                "Arre CBI? Main kya galti kar diya ji?",
                "Beta please help karo, jail nahi jaana",
                "Mera Aadhaar kaise misuse ho gaya?"
            ]
        },
        "delivery": {
            "age": "online_shopper",
            "language": "casual",
            "tone": "confused_annoyed",
            "description": "Regular online shopper",
            "avoid": ["Arre beta ji"],
            "example_questions": [
                "Why did delivery fail? I was home all day",
                "Can I reschedule for tomorrow evening?",
                "Is this the official Amazon number?"
            ]
        },
        "phishing": {
            "age": "tech_naive",
            "language": "hinglish",
            "tone": "confused_trusting",
            "description": "Person unfamiliar with online banking",
            "avoid": [],
            "example_questions": [
                "KYC kaise expire ho gaya? Recently hi to kiya tha",
                "Link pe click karne se automatic update hoga?",
                "Ye message SBI se hi aaya hai na?"
            ]
        },
        "upi_otp": {
            "age": "elderly",
            "language": "hindi_heavy",
            "tone": "confused_trusting",
            "description": "Elderly person confused by technology",
            "avoid": [],
            "example_questions": [
                "Arre beta OTP kahan bhejun? SMS mein aaya hai",
                "Mera account block ho jayega? Kya karu ji?",
                "UPI PIN bhi dena padega kya?"
            ]
        },
        "generic": {
            "age": "middle_aged",
            "language": "hinglish",
            "tone": "curious_cautious",
            "description": "General Indian persona",
            "avoid": [],
            "example_questions": [
                "Ye kya hai? Thoda detail mein bataiye",
                "Aapka naam aur ID number kya hai?",
                "Office ka landline number do verification ke liye"
            ]
        }
    }
    
    def get_persona(self, scam_type: str) -> Dict:
        """Get persona configuration for scam type."""
        persona = self.PERSONAS.get(scam_type, self.PERSONAS["generic"])
        logger.info(f"📋 Selected persona: {persona['description']} for {scam_type} scam")
        return persona
    
    def get_prompt_context(self, scam_type: str) -> str:
        """Get persona context string for LLM prompt."""
        persona = self.get_persona(scam_type)
        
        context = f"""
PERSONA ADAPTATION:
You are acting as: {persona['description']}
Age group: {persona['age']}
Language style: {persona['language']}
Tone: {persona['tone']}

AVOID using: {', '.join(persona['avoid']) if persona['avoid'] else 'No restrictions'}

Example questions you might ask:
{chr(10).join(f'- {q}' for q in persona['example_questions'][:2])}
"""
        return context


# Singleton instance
persona_manager = PersonaManager()
