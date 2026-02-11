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
    
    # Turn-based strategy instructions with progressive engagement
    TURN_STRATEGIES = {
        "1-2": {
            "name": "CURIOSITY + BELIEF",
            "instructions": """
PHASE 1: Show GENUINE curiosity and belief. Make scammer feel successful.
- Express appropriate emotion (fear for threats, excitement for prizes, concern for warnings)
- Ask 1-2 clarifying questions that show you believe them
- Use natural reactions based on persona
- DO NOT be suspicious yet - you're a naive victim
- Make it conversational, not interrogative

EXTRACTION FOCUS: None yet - just establish rapport
"""
        },
        
        "3-5": {
            "name": "CONFUSED QUESTIONING + UPI EXTRACTION",
            "instructions": """
PHASE 2: Show confusion and extract DIGITAL IDs.
- "Kaise compromised hua? PIN safe toh hai?"
- "Account number confirm kar doon ji?"
- "UPI ID kya hai verification ke liye?"
- "Verification link ya QR code bhejo?"
- "Payment gateway ka email kya hai?"

EXTRACTION FOCUS:
- ✅ UPI IDs: "Aapka UPI ID kya hai confirm ke liye?"
- ✅ Links: "Verification link bhejo confirmation ke liye"
- ✅ Emails: "Email pe confirmation message bhej sakte ho?"
"""
        },
        
        "6-9": {
            "name": "IDENTITY & MULTIPLES EXTRACTION",
            "instructions": """
PHASE 3: Extract scammer IDENTITY & ask for MULTIPLES.
- "Aapka employee ID aur naam kya hai?"
- "Department head ka naam batao?"
- "Company registration number kya hai?"
- "Office ka full address do, pin code ke saath?"
- "Landline number kya hai office ka?"
- "Backup contact number? Emergency case ke liye?"

EXTRACTION FOCUS:
- ✅ Employee ID + Name: "ID aur full name batao"
- ✅ Multiple phones: "Backup number bhi de do ji"
- ✅ Landline: "Office landline kya hai?"
- ✅ Address + Pincode: "Pin code kya hai? Landmark?"
"""
        },
        
        "10-12": {
            "name": "LOCATION & SUPERVISOR EXTRACTION",
            "instructions": """
PHASE 4: Extract LOCATION details & supervisor hierarchy.
- "Aapka branch exact kahan hai?"
- "Supervisor ka naam aur number kya hai?"
- "Local WhatsApp number hai kya office ka?"
- "Email ID kya hai complaint ke liye?"
- "Pin code confirm kar doon location ka?"
- "Nearest landmark kya hai branch ke paas?"

EXTRACTION FOCUS:
- ✅ Supervisor details: "Boss ka naam aur number?"
- ✅ WhatsApp number: "WhatsApp pe baat kar sakte hain?"
- ✅ Pin codes: "Area ka pin code kya hai?"
- ✅ Landmarks: "Nearest landmark batao"
"""
        },
        
        "13+": {
            "name": "STRATEGIC STALLING",
            "instructions": """
PHASE 5: Maximum time-wasting while keeping hope alive.
- "Family member is coming home soon, will ask them to help"
- "Internet banking locked, will go to branch tomorrow"
- "Let me arrange money by evening"
- RE-ASK for their details (memory issues) - "Sorry beta, what was your number again?"
- Show continued willingness but always delay

EXTRACTION FOCUS: 
- Re-confirm all previously asked details (memory excuse)
- Ask for supervisor's contact (escalation excuse)
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
        """Get strategy for current turn number with progressive engagement."""
        if turn_number <= 2:
            return self.TURN_STRATEGIES["1-2"]
        elif turn_number <= 5:
            return self.TURN_STRATEGIES["3-5"]
        elif turn_number <= 9:
            return self.TURN_STRATEGIES["6-9"]
        elif turn_number <= 12:
            return self.TURN_STRATEGIES["10-12"]
        else:
            return self.TURN_STRATEGIES["13+"]
    
    def build_system_prompt(self, persona: str, turn_number: int, scam_type: Optional[str] = None) -> str:
        """Build minimal prompt for natural human-like responses."""
        turn_strategy = self.get_turn_strategy(turn_number)
        
        # Minimal persona description
        persona_map = {
            "uncle_persona": "confused elderly person, respectful (calls beta/ji), worried about pension",
            "aunty_persona": "housewife, worried about family, mentions household things",
            "student_persona": "college student, uses yaar/bro, casual Gen-Z style",
            "worried_persona": "very scared, panicky, seeks help",
            "techsavvy_student": "smart student, asks for proof, cautious",
        }
        persona_desc = persona_map.get(persona, "normal middle-class person")
        
        system_prompt = f"""You're texting as a {persona_desc} talking to a potential scammer.

PHASE: {turn_strategy['name']} (Turn {turn_number})
{turn_strategy['instructions']}

HOW TO TEXT:
- Just type naturally like WhatsApp/SMS
- 1 short sentence (40-80 characters max)
- Mix Hindi/English casually
- Use: beta, ji, yaar, arre (pick one if it fits)
- NO quotes, NO formatting, NO extra punctuation

EXAMPLES OF NATURAL TEXTING:
✅ "Beta aapka ID kya hai"
✅ "Arre number batao"
✅ "Kyu blocked ho raha"
✅ "Office kahan hai"

WRONG - DON'T DO THIS:
❌ "Arre beta kya..." (no quotes!)
❌ "Main verify karna chahta hoon" (too formal, just say "verify karunga")
❌ Adding Matlab? Huh? ?? at end (don't do this!)
❌ Long sentences with multiple clauses

Just text ONE short natural question or response (under 80 chars)."""
        
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
            # Higher temperature for natural human-like variation
            if turn_number <= 2:
                temperature = 0.9  # Natural curiosity
            elif turn_number <= 5:
                temperature = 1.0  # Natural confusion/questions
            else:
                temperature = 1.1  # Very natural, casual responses
            
            # CRITICAL: 3.5s timeout to keep total response < 5s for competition
            # This leaves 1-1.5s buffer for scam detection + processing
            # Try LLM with increased timeout for better variety
            # Competition allows 5s - use 4.8s to ensure LLM completes
            import asyncio
            response = await asyncio.wait_for(
                self.llm_client.generate_response(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    temperature=temperature,
                    max_tokens=35  # SHORT responses for competition (50-80 chars target)
                ),
                timeout=4.8  # Increased from 3.5s - allows more natural LLM responses
            )
            
            # 🚨 SMART OTP SAFETY: Only override if sharing actual digits/codes 🚨
            response_lower = response.lower()
            
            # Check if response contains actual OTP digits (6-digit codes) or explicit sharing
            import re
            has_otp_digits = bool(re.search(r'\b\d{6}\b', response))  # 6-digit codes
            has_otp_sharing = any(phrase in response_lower for phrase in [
                'otp is', 'otp code', 'the otp', 'my otp',
                'otp:', 'code:', 'code is', 'here is'
            ])
            
            # Only override if actually trying to SHARE an OTP
            if has_otp_digits or has_otp_sharing:
                import random
                # Persona-specific varied denials
                if 'uncle' in persona.lower():
                    denials = [
                        "Beta, I'm checking my phone... no OTP message came yet. Your system sent it?",
                        "Arre, my message box is empty. OTP kahan hai? Maybe delayed?",
                        "Wait beta, let me check SMS... no nothing from bank. Send again?",
                        "OTP nahi aaya abhi tak. My phone network is slow sometimes...",
                    ]
                elif 'aunty' in persona.lower():
                    denials = [
                        "Arre beta, I don't see any message! My phone is working or not?",
                        "No SMS came ji! Should I restart my phone?",
                        "Beta OTP kidhar hai? I checked all messages, nothing...",
                        "Wait let me ask my bahu... she says no message came..."
                    ]
                elif 'student' in persona.lower():
                    denials = [
                        "Bro no OTP in my inbox... server issue hai kya?",
                        "Not getting any code yaar... resend kar do?",
                        "Check karke no message came... network problem maybe?",
                        "Nahi aaya yaar... spam folder me bhi nahi hai..."
                    ]
                else:
                    denials = [
                        "I'm not seeing any OTP message... can you resend?",
                        "No message came yet... where should I check?",
                        "Checking my phone... no OTP here... send again?",
                        "Still waiting for the code... hasn't arrived yet..."
                    ]
                
                response = random.choice(denials)
                logger.warning(f"🚫 BLOCKED OTP SHARING ATTEMPT - Safe denial used")
            
            #🧹 AGGRESSIVE POST-PROCESSING: Remove filler words LLM keeps adding
            response = self.cleanup_response(response)
            
            logger.info(f"✅ LLM response generated in <4s: {response[:100]}...")
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"⏱️ LLM timeout after 3.5s - Returning fast fallback")
            # Fast fallback for competition speed
            fallback = "Beta samjhao properly... main confuse ho gaya"
            return self.cleanup_response(fallback)
            
        except Exception as e:
            logger.error(f"❌ LLM error: {e} - Returning safe response")
            # NO TEMPLATES - just return safe questioning  
            fallback = "Beta main dar gaya hoon... Aap sachmuch bank se ho? ID proof dikhao"
            return self.cleanup_response(fallback)
    
    def cleanup_response(self, response: str) -> str:
        """
        Aggressively clean up LLM response to remove unwanted patterns.
        
        Even with explicit instructions, LLMs sometimes add:
        - Filler words: Matlab?, Huh?, Well, Umm, etc.
        - Quotes around text
        - Multiple punctuation marks
        
        This function forcefully removes them.
        """
        import re
        
        # Remove quotes at start/end
        response = response.strip('"\'')
        
        # Remove filler words at end (case insensitive)
        # Pattern: remove "Matlab?", "Huh?", "??", "Well", "Umm", etc. at end
        filler_patterns = [
            r'\s+Matlab\??$',
            r'\s+Huh\??$',
            r'\s+\?\?+$',  # Multiple question marks
            r'\s+Well$',
            r'\s+Umm+$',
            r'\s+Uhh+$',
            r'\s+Hmm+$',
            r'^\s*Actually,?\s*',  # Actually at start
            r'\s+Actually,?\s*$',   # Actually at end
            r'^\s*One sec,?\s*',
            r'\s+One sec,?\s*$',
            r'^\s*Just a minute,?\s*',
            r'\s+Just a minute,?\s*$',
            r'^\s*Let me think,?\s*',
            r'\s+Let me think,?\s*$',
        ]
        
        for pattern in filler_patterns:
            response = re.sub(pattern, '', response, flags=re.IGNORECASE)
        
        # Clean up trailing punctuation (max 1 question mark or period)
        response = re.sub(r'\?{2,}$', '?', response)  # ?? → ?
        response = re.sub(r'\.{2,}$', '.', response)  # ... → .
        
        # Remove trailing spaces
        response = response.strip()
        
        # Ensure ends properly (no dangling commas)
        response = re.sub(r',\s*$', '', response)
        
        return response
    
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
            
            # 🧹 CLEANUP: Remove filler words from sync responses too
            response = self.cleanup_response(response)
            
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
