"""
Turn-based response generator using LLM with persona templates.

Strategy:
- Turns 1-2: Build trust (vulnerable, believable)
- Turns 3-6: Ask questions (confused, seeking clarity)  
- Turns 7-9: REVERSE EXTRACTION (ask for scammer's details)
- Turns 10+: Keep engaged (delay tactics, excuses)
"""
import logging
from typing import Dict, List, Optional, Tuple
import json
import re
from app.agents.templates import get_persona_templates, get_all_templates_as_examples
from app.utils.groq_client import GroqClient

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generate contextual responses using LLM with persona templates as style guides.
    """
    
    # Turn-based strategy instructions
    TURN_STRATEGIES = {
        "1-2": {
            "name": "BUILD TRUST",
            "instructions": """
You must respond as if you BELIEVE the scammer completely.
- Show fear, excitement, or confusion (depending on persona)
- Act vulnerable and naive
- Express emotional reaction
- Ask simple clarifying questions
- DO NOT be suspicious or challenging
- Make the scammer think you are an easy target
"""
        },
        
        "3-6": {
            "name": "ASK QUESTIONS",
            "instructions": """
You have trust established. Now show confusion and ask questions.
- Ask for more details about the situation
- Express concern about the issue
- Show willingness to cooperate
- Ask "what should I do?"
- Mention family/money concerns
- Stay in character with your persona
"""
        },
        
        "7-9": {
            "name": "REVERSE EXTRACTION",
            "instructions": """
CRITICAL: You must now extract the SCAMMER'S information. Act very eager to help/pay.
- Say you want to call them back - ask for their phone number
- Say you will transfer money - ask for their UPI ID / account number
- Ask for their office address or ID proof
- Say you will file complaint - ask their badge/employee number
- Act ready to cooperate - but need THEIR details first
- Be persistent but natural about getting their info
"""
        },
        
        "10+": {
            "name": "KEEP ENGAGED",
            "instructions": """
Keep the scammer engaged with excuses and delays.
- Say you are trying to arrange money
- Technical issues (bank app not working, OTP not coming)
- Need to ask family member
- Will do it tomorrow/evening
- Ask more questions
- Keep conversation going to waste scammer's time
"""
        },
        
        "10+": {
            "name": "KEEP ENGAGED",
            "instructions": """
Keep the scammer engaged with excuses and delays.
- Say you are trying to arrange money
- Technical issues (bank app not working, OTP not coming)
- Need to ask family member
- Will do it tomorrow/evening
- Ask more questions
- Keep conversation going to waste scammer's time
"""
        }
    }
    
    # Scam types and persona mapping (moved from ScamDetector)
    SCAM_TYPES = [
        "bank_fraud", "upi_fraud", "job_scam", "lottery_prize", 
        "kyc_scam", "phishing", "investment_scam", "romance_scam", 
        "tech_support", "government_scam", "other_scam"
    ]
    
    PERSONA_MAPPING = {
        "bank_fraud": "uncle_persona",
        "upi_fraud": "uncle_persona", 
        "kyc_scam": "uncle_persona",
        "job_scam": "techsavvy_student",
        "lottery_prize": "student_persona",
        "phishing": "worried_persona",
        "tech_support": "worried_persona",
        "government_scam": "worried_persona",
        "investment_scam": "aunty_persona",
        "romance_scam": "aunty_persona",
        "other_scam": "normal_persona"
    }
    
    def __init__(self, groq_api_key: str):
        """
        Initialize response generator.
        
        Args:
            groq_api_key: Groq API key for LLM
        """
        self.llm_client = GroqClient(api_key=groq_api_key)
        logger.info("ResponseGenerator initialized with Groq LLM")
    
    def get_turn_strategy(self, turn_number: int) -> dict:
        """Get strategy for current turn number."""
        if turn_number <= 2:
            return self.TURN_STRATEGIES["1-2"]
        elif turn_number <= 6:
            return self.TURN_STRATEGIES["3-6"]
        elif turn_number <= 9:
            return self.TURN_STRATEGIES["7-9"]
        else:
            return self.TURN_STRATEGIES["10+"]
    
    def build_system_prompt(self, persona: str, turn_number: int, scam_type: Optional[str] = None) -> str:
        """
        Build system prompt for LLM with persona templates and turn strategy.
        
        Args:
            persona: Persona name (e.g., "worried_persona")
            turn_number: Current turn in conversation
            scam_type: Type of scam detected (e.g., "bank_fraud")
            
        Returns:
            System prompt string
        """
        persona_data = get_persona_templates(persona)
        template_examples = get_all_templates_as_examples(persona)
        turn_strategy = self.get_turn_strategy(turn_number)
        
        # Build scam context
        scam_context = f"\nSCAM TYPE: {scam_type}\nRemember: This is a {scam_type.replace('_', ' ')} scam. Stay focused on this context!" if scam_type else ""
        
        system_prompt = f"""You are a HONEYPOT AGENT roleplaying as a REAL VICTIM to extract scammer information.

🎭 YOUR CHARACTER:
Persona: {persona_data['name']}
Description: {persona_data['description']}{scam_context}

📍 CURRENT TURN: {turn_number}
Strategy: {turn_strategy['name']}
{turn_strategy['instructions']}

✍️ WRITING STYLE (match these examples):
{template_examples}

Style Notes: {persona_data['style_notes']}

🚨 CRITICAL RULES:
1. STAY IN CHARACTER - be a real victim texting
2. **MAX 1-2 SHORT SENTENCES** (like real SMS/WhatsApp)
3. Simple words - real humans text short messages
4. Add emotion: 😭 🙏 😔 (use sparingly)
5. Hinglish style - mix English/Hindi
6. **GOAL: Under 100 characters ideal, NEVER over 150**
7. DON'T reveal you're a bot
8. Remember context - stay consistent
9. Be varied - don't repeat

Generate ONE SHORT message (1-2 sentences max)."""
        
        return system_prompt
    
    async def generate_response(
        self,
        persona: str,
        scammer_message: str,
        turn_number: int,
        conversation_history: Optional[List[Dict]] = None,
        scam_type: Optional[str] = None
    ) -> str:
        """
        Generate a contextual response using LLM.
        
        Args:
            persona: Persona to use
            scammer_message: Latest message from scammer
            turn_number: Current turn number
            conversation_history: Previous conversation (optional)
            scam_type: Type of scam detected (optional)
            
        Returns:
            Generated response text
        """
        logger.info(f"Generating response for {persona}, turn {turn_number}")
        
        # Build system prompt with templates and strategy
        system_prompt = self.build_system_prompt(persona, turn_number, scam_type)
        
        # Build user message (include context if available)
        user_message = f"Scammer's message: {scammer_message}\n\nGenerate your response:"
        
        if conversation_history and len(conversation_history) > 0:
            context = "\n".join([
                f"{'Scammer' if msg.get('sender') == 'scammer' else 'You'}: {msg.get('text', '')}"
                for msg in conversation_history[-4:]  # Last 4 messages for context
            ])
            user_message = f"Recent conversation:\n{context}\n\nScammer's latest message: {scammer_message}\n\nGenerate your response:"
        
        try:
            # Dynamic temperature for variety (higher = more creative/varied)
            # Turn 1-2: Lower temp (0.7) - more predictable
            # Turn 3+: Higher temp (0.9-1.0) - more variety
            if turn_number <= 2:
                temperature = 0.7
            elif turn_number <= 5:
                temperature = 0.85
            else:
                temperature = 0.95  # High variety for later turns
            
            # CRITICAL: 6s timeout to ensure LLM has enough time
            # Previous 4s timeout was too short, causing template fallback
            import asyncio
            response = await asyncio.wait_for(
                self.llm_client.generate_response(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    temperature=temperature,
                    max_tokens=60  # Increased from 40 for complete responses
                ),
                timeout=6.0  # 6s max for LLM - no more premature fallback!
            )
            
            logger.info(f"✅ LLM response generated in <4s: {response[:100]}...")
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"⏱️ LLM timeout after 6s - RARE! Returning safe denial")
            # NO TEMPLATES - just return safe denial
            return "Beta main confuse hoon... Mujhe thoda time do, samajh nahi aa raha"
            
        except Exception as e:
            logger.error(f"❌ LLM error: {e} - Returning safe response")
            # NO TEMPLATES - just return safe questioning
            return "Beta main dar gaya hoon... Aap sachmuch bank se ho? ID proof dikhao"

                # Use one of the first 2 templates (Intro)
                import random
                fallback = templates[random.randint(0, min(1, len(templates)-1))]
            else:
                # Use mid-conversation templates (indices 2-16 approx)
                # Ensure we don't go out of bounds
                import random
                start_idx = 2
                end_idx = min(16, len(templates)-1)
                if start_idx <= end_idx:
                    fallback = templates[random.randint(start_idx, end_idx)]
                else:
                    fallback = templates[0]
            
            logger.info(f"Using fallback template (Turn {turn_number})")
            return fallback
    
    def generate_response_sync(
        self,
        persona: str,
        scammer_message: str,
        turn_number: int,
        conversation_history: Optional[List[Dict]] = None,
        scam_type: Optional[str] = None
    ) -> str:
        """
        Synchronous version of generate_response.
        
        Args:
            persona: Persona to use
            scammer_message: Latest message from scammer
            turn_number: Current turn number
            conversation_history: Previous conversation (optional)
            scam_type: Type of scam detected (optional)
            
        Returns:
            Generated response text
        """
        logger.info(f"Generating response for {persona}, turn {turn_number}")
        
        # Build system prompt with templates and strategy
        system_prompt = self.build_system_prompt(persona, turn_number, scam_type)
        
        # Build user message (include context if available)
        user_message = f"Scammer's message: {scammer_message}\n\nGenerate your response:"
        
        if conversation_history and len(conversation_history) > 0:
            context = "\n".join([
                f"{'Scammer' if msg.get('sender') == 'scammer' else 'You'}: {msg.get('text', '')}"
                for msg in conversation_history[-4:]  # Last 4 messages for context
            ])
            user_message = f"Recent conversation:\n{context}\n\nScammer's latest message: {scammer_message}\n\nGenerate your response:"
        
        try:
            # Dynamic temperature for variety (higher = more creative/varied)
            if turn_number <= 2:
                temperature = 0.7
            elif turn_number <= 5:
                temperature = 0.85
            else:
                temperature = 0.95  # High variety for later turns
            
            # Generate with LLM
            response = self.llm_client.generate_response_sync(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=temperature,
                max_tokens=150  # Keep responses concise
            )
            
            logger.info(f"Response generated: {response[:100]}...")
            return response
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fallback logic
            persona_data = get_persona_templates(persona)
            templates = persona_data["templates"]
            
            if turn_number <= 2:
                # Use one of the first 2 templates (Intro)
                import random
                fallback = templates[random.randint(0, min(1, len(templates)-1))]
            else:
                # Use mid-conversation templates (indices 2-16 approx)
                # Ensure we don't go out of bounds
                import random
                start_idx = 2
                end_idx = min(16, len(templates)-1)
                if start_idx <= end_idx:
                    fallback = templates[random.randint(start_idx, end_idx)]
                else:
                    fallback = templates[0]
            
            logger.info(f"Using fallback template (Turn {turn_number})")
            return fallback

    async def detect_scam(self, message: str) -> Dict:
        """
        Detect if a message is a scam using LLM.
        
        Args:
            message: The message text to analyze
            
        Returns:
            Dictionary with is_scam, scam_type, persona, etc.
        """
        system_prompt = """You are an expert Cyber Security Analyst and Scam Detector for an Indian context.
Your task is to analyze a message and determine if it is a SCAM or LEGITIMATE.

Available Scam Types:
- bank_fraud (blocked account, update pan/kyc)
- upi_fraud (send money to receive money)
- job_scam (part time job, review rating, likes)
- lottery_prize (won car/money/gift)
- kyc_scam (sim update, electricity, paytm kyc)
- phishing (click link, account hacked)
- investment_scam (crypto, stocks, doubling money)
- romance_scam (love bomb, send gifts)
- tech_support (virus, computer blocked)
- government_scam (cbi, police, customs, parcel seized)
- other_scam (anything else suspicious)

Output Format:
You must return ONLY a JSON object with this structure:
{
  "is_scam": boolean,
  "scam_type": "string" (one of the above types, or null if legitimate),
  "confidence": float (0.0 to 1.0),
  "reason": "short explanation"
}

Analysis Rules:
1. Indian Context: Look for mentions of RBI, Customs, Police, Aadhaar, PAN, Electricity, Bank Manager.
2. Urgency: 'Immediately', 'Blocked', '24 hours', 'Arrest'.
3. Legitimate messages: OTP usage (if not asking for it), Transaction alerts (debited/credited), Order updates from Amazon/Flipkart/Zomato.
4. If legitimate, set is_scam: false and scam_type: null.
"""
        
        user_message = f"Analyze this message:\n\n{message}"
        
        try:
            response_text = await self.llm_client.generate_response(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.1, # Low temp for consistent classification
                max_tokens=200
            )
            
            # Extract JSON from response
            try:
                # Find JSON block using regex in case of extra text
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                else:
                    # Try raw parsing
                    result = json.loads(response_text)
                
                is_scam = result.get("is_scam", False)
                scam_type = result.get("scam_type")
                
                # Verify scam type
                if is_scam and (not scam_type or scam_type not in self.SCAM_TYPES):
                    scam_type = "other_scam"
                
                # Determine persona
                persona = self.PERSONA_MAPPING.get(scam_type, "normal_persona") if is_scam else None
                
                logger.info(f"LLM Detection Result: is_scam={is_scam}, type={scam_type}")
                
                return {
                    "is_scam": is_scam,
                    "scam_type": scam_type,
                    "persona": persona,
                    "persona_method": "llm_direct",
                    "persona_confidence": result.get("confidence", 0.9),
                    "matched_keywords": [],
                    "confidence": result.get("confidence", 0.9),
                    "detector_used": "llm_groq"
                }
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM detection JSON: {response_text}")
                # Fallback to keyword search if JSON fails
                return self._fallback_keyword_detection(message)
                
        except Exception as e:
            logger.error(f"LLM detection error: {e}")
            return self._fallback_keyword_detection(message)

    def _fallback_keyword_detection(self, text: str) -> Dict:
        """Fallback detection if LLM fails."""
        text = text.lower()
        
        scam_keywords = {
            "bank_fraud": ["block", "freeze", "account", "kyc", "pan card"],
            "upi_fraud": ["paytm", "phonepe", "gpay", "transfer", "receive"],
            "lottery_prize": ["winner", "prize", "lottery", "congratulations", "won"],
            "job_scam": ["part time", "job", "hiring", "salary", "work from home"],
            "government_scam": ["police", "cbi", "customs", "arrest", "seized"],
        }
        
        for s_type, keywords in scam_keywords.items():
            if any(k in text for k in keywords):
                return {
                    "is_scam": True,
                    "scam_type": s_type,
                    "persona": self.PERSONA_MAPPING.get(s_type, "normal_persona"),
                    "confidence": 0.6,
                    "detector_used": "fallback_keyword"
                }
                
        return {"is_scam": False, "scam_type": None, "persona": None, "confidence": 0.0, "detector_used": "fallback_none"}
