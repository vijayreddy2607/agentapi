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
from app.prompts.uncle_persona import UNCLE_SYSTEM_PROMPT, UNCLE_FEW_SHOT_EXAMPLES
from app.prompts.worried_persona import WORRIED_SYSTEM_PROMPT, WORRIED_FEW_SHOT_EXAMPLES
from app.prompts.techsavvy_persona import TECHSAVVY_SYSTEM_PROMPT, TECHSAVVY_FEW_SHOT_EXAMPLES
from app.prompts.student_persona import STUDENT_SYSTEM_PROMPT, STUDENT_FEW_SHOT_EXAMPLES
from app.prompts.aunty_persona import AUNTY_SYSTEM_PROMPT, AUNTY_FEW_SHOT_EXAMPLES

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
            "name": "NATURAL QUESTIONING",
            "instructions": """
PHASE 3: Ask NATURAL confused questions (not obvious extraction!).
- "Aapka naam kya hai?"
- "Company/Bank ka naam?"
- "Kahan se call kar rahe ho?"
- "Number kya hai aapka?"
- "Correct hai na ye?"

EXTRACTION FOCUS:
- ✅ Names: "Aapka naam batao?"
- ✅ Phone: "Number do contact ke liye"
- ✅ Company: "Company/Bank ka naam?"
- ❌ DON'T ask: Employee ID, full address with pincode (too obvious!)
"""
        },
        
        "10-12": {
            "name": "NATURAL SKEPTICISM",
            "instructions": """
PHASE 4: Show natural doubt and ask simple verification questions.
- "Beta check kar loon kya?"
- "Thik hai, wait karo"
- "Number aur naam confirm kar loon?"
- "Bank pe confirm kar loon?"

EXTRACTION FOCUS:
- ✅ Re-confirm: "Number phir se batao?"
- ✅ Simple verification: "Naam kya tha?"
- ❌ DON'T ask for: Supervisor, pin codes, landmarks (too systematic!)
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
        # Uncle: bank/KYC/UPI scams (confused elderly)
        "bank_fraud": "uncle_persona",
        "upi_fraud": "uncle_persona",
        "kyc_scam": "uncle_persona",
        "govt_scheme": "uncle_persona",
        # Student: job/loan scams (excited youth)
        "job_scam": "student_persona",
        "loan_scam": "student_persona",
        # TechSavvy: investment/crypto/tech scams (skeptical professional)
        "investment_scam": "techsavvy_persona",
        "crypto": "techsavvy_persona",
        "tech_support": "techsavvy_persona",
        # Worried: billing/legal/credit/delivery (panicked adult)
        "phishing": "worried_persona",
        "government_scam": "worried_persona",
        "credit_card": "worried_persona",
        "police_legal": "worried_persona",
        "tax_refund": "worried_persona",
        "bill_payment": "worried_persona",
        "electricity": "worried_persona",
        "delivery": "worried_persona",
        # Aunty: lottery/romance (warm social)
        "lottery_prize": "aunty_persona",
        "romance_scam": "aunty_persona",
        "prize_lottery": "aunty_persona",
        # Default
        "other_scam": "uncle_persona"
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
    
    # Enhanced persona system prompts (imported from persona files)
    ENHANCED_PERSONA_PROMPTS = {
        "uncle_persona": UNCLE_SYSTEM_PROMPT,
        "worried_persona": WORRIED_SYSTEM_PROMPT,
        "techsavvy_persona": TECHSAVVY_SYSTEM_PROMPT,
        "student_persona": STUDENT_SYSTEM_PROMPT,
        "aunty_persona": AUNTY_SYSTEM_PROMPT,
    }

    ENHANCED_PERSONA_EXAMPLES = {
        "uncle_persona": UNCLE_FEW_SHOT_EXAMPLES,
        "worried_persona": WORRIED_FEW_SHOT_EXAMPLES,
        "techsavvy_persona": TECHSAVVY_FEW_SHOT_EXAMPLES,
        "student_persona": STUDENT_FEW_SHOT_EXAMPLES,
        "aunty_persona": AUNTY_FEW_SHOT_EXAMPLES,
    }

    # Maps alternate persona name variants to canonical keys
    PERSONA_ALIASES = {
        "uncle": "uncle_persona",
        "worried": "worried_persona",
        "techsavvy": "techsavvy_persona",
        "techsavvy_student": "techsavvy_persona",
        "techsavvy_persona": "techsavvy_persona",
        "student": "student_persona",
        "aunty": "aunty_persona",
        "sunita": "aunty_persona",
        "uncle_persona": "uncle_persona",
        "worried_persona": "worried_persona",
        "student_persona": "student_persona",
        "aunty_persona": "aunty_persona",
    }

    def build_system_prompt(self, persona: str, turn_number: int, scam_type: Optional[str] = None) -> str:
        """Build system prompt — uses full enhanced persona prompt for all 5 personas."""
        turn_strategy = self.get_turn_strategy(turn_number)

        # Normalize persona name to canonical key
        persona_key = self.PERSONA_ALIASES.get(persona.lower(), "uncle_persona")
        base_prompt = self.ENHANCED_PERSONA_PROMPTS[persona_key]

        system_prompt = (
            f"{base_prompt}\n\n"
            f"🎯 CURRENT PHASE: {turn_strategy['name']} (Turn {turn_number})\n"
            f"{turn_strategy['instructions'].strip()}\n\n"
            "🚨 SECURITY RULES:\n"
            "- NEVER share OTP/PIN/CVV numbers\n"
            "- If asked for OTP → turn into extraction question (ask their name/number/ID)\n"
            "- Keep response under 120 characters, 1-2 sentences only"
        )
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
                for msg in conversation_history[-8:]  # Last 4 messages for context
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
            
            # 🚨 STRICT OTP/PIN/CVV SAFETY: NEVER share any sensitive numbers 🚨
            response_lower = response.lower()
            
            # Check if response mentions OTP/PIN/CVV or contains digits being shared
            import re
            
            # Block ANY digit patterns when OTP/PIN/CVV is in context
            has_sensitive_context = any(word in response_lower for word in [
                'otp', 'pin', 'cvv', 'password', 'code', 'passcode'
            ])
            
            # Block digit patterns (4-8 digits) near sensitive keywords
            has_digits_shared = bool(re.search(r'\b\d{3,8}\b', response))
            
            # Block explicit sharing phrases
            has_sharing_intent = any(phrase in response_lower for phrase in [
                'otp is', 'otp hai', 'code is', 'code hai', 'pin is', 'pin hai',
                'otp:', 'code:', 'pin:', 'here is', 'yeh hai', 'this is'
            ])
            
            # ALWAYS override if ANY of these conditions met
            if (has_sensitive_context and has_digits_shared) or has_sharing_intent:
                import random
                # Persona-specific EXTRACTION tactics (never reveal OTP, ask for THEIR info!)
                if 'uncle' in persona.lower():
                    denials = [
                        "Haan beta OTP bhej dunga, par pehle aapka WhatsApp number kya hai?",
                        "Thik hai beta kar dunga, par aapka website link aur number batao ji?",
                        "Beta main send kar dunga, par pehle aapka official number aur email ID do",
                        "Arre haan kar dunga, par verification ke liye aapka website kya hai?",
                        "Thik hai beta bhejunga, par pehle aapka customer care number batao"
                    ]
                elif 'aunty' in persona.lower():
                    denials = [
                        "Haan beta bhej dungi, par pehle aapka number aur naam batao ji?",
                        "Beta thik hai bhejungi, par aapka WhatsApp number kya hai confirm ke liye?",
                        "Arre bhej dungi beta, par pehle aapka website link aur email ID do",
                        "Beta kar dungi, par aapka office ka phone number batao verification ke liye?"
                    ]
                elif 'student' in persona.lower():
                    denials = [
                        "Sure bro I'll send it, but first what's your number and employee ID?",
                        "OK I'll do it, but what's your WhatsApp number and website link?",
                        "Yeah I'll send it, but first give me your official email and number",
                        "Alright I'll share it, but need your contact details for verification first"
                    ]
                else:
                    denials = [
                        "Haan bhej dunga, par pehle aapka number aur website link batao",
                        "Thik hai kar dunga, par aapka WhatsApp number kya hai?",
                        "Ji send kar dunga, par pehle aapka official contact details do"
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
            logger.error(f"❌ ALL LLMs FAILED: {e}")
            logger.warning(f"🚨 Using emergency fallback for {persona} turn {turn_number}")
            
            # Use emergency turn-aware fallback
            fallback = self._get_emergency_fallback(
                persona=persona,
                turn_number=turn_number,
                scammer_message=scammer_message
            )
            
            # Log for monitoring
            logger.critical(f"🔴 LLM FAILURE - Emergency fallback used: {fallback[:50]}...")
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
                for msg in conversation_history[-8:]  # Last 4 messages for context
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
    
    def _get_emergency_fallback(self, persona: str, turn_number: int, scammer_message: str) -> str:
        """
        Emergency fallback if ALL LLMs fail.
        Still extracts intelligence using turn-aware templates.
        
        Strategy:
        - Turn 1-3: Build trust (confusion, questions)
        - Turn 4-6: Extract contact info (phone, email, website)
        - Turn 7-10: Extract credentials (employee ID, office, manager)
        - Turn 11+: Delay tactics
        """
        import random
        
        persona_lower = persona.lower()
        
        # TURN 1-3: Build Trust / Show Confusion
        if turn_number <= 3:
            if 'uncle' in persona_lower:
                return random.choice([
                    "Arre beta, ye kya ho gaya? Samjha do zara",
                    "Beta main samajh nahi paya, phir se batao",
                    "Kya karna hai beta? Main confuse ho gaya"
                ])
            elif 'aunty' in persona_lower:
                return random.choice([
                    "Beta samajh nahi aayi baat, dobara batao",
                    "Arre kya bol rahe ho beta? Confusion ho rahi hai",
                    "Main thoda confuse hoon beta, explain karo"
                ])
            elif 'student' in persona_lower:
                return random.choice([
                    "Wait what? Can you explain that again?",
                    "Confused bro, what do you mean?",
                    "Hold on, what's happening exactly?"
                ])
            elif 'worried' in persona_lower:
                return random.choice([
                    "Ji sir main samajh nahi paya",
                    "Sir confusion ho rahi hai, kya karna hai?",
                    "Ji kya karna hai sir? Batao please"
                ])
            else:  # techsavvy
                return random.choice([
                    "Hold on, I didn't catch that",
                    "Can you clarify what you need?",
                    "I'm not following, explain again"
                ])
        
        # TURN 4-6: Extract Contact Info
        elif turn_number <= 6:
            if 'uncle' in persona_lower:
                return random.choice([
                    "Thik hai beta, par pehle aapka number batao",
                    "Arre aapka WhatsApp number kya hai?",
                    "Beta aapka email ID kya hai?",
                    "Website link bhejo verify ke liye"
                ])
            elif 'aunty' in persona_lower:
                return random.choice([
                    "Beta pehle aapka number do ji",
                    "Aapka WhatsApp number kya hai beta?",
                    "Email ID bhejo pehle",
                    "Website link kya hai beta?"
                ])
            elif 'student' in persona_lower:
                return random.choice([
                    "OK but what's your number first?",
                    "Sure, but send me your WhatsApp number",
                    "What's your email ID?",
                    "Send me the website link"
                ])
            elif 'worried' in persona_lower:
                return random.choice([
                    "Ji sir aapka phone number kya hai?",
                    "Sir aapka email ID chahiye",
                    "Office ka contact number batao sir",
                    "Website address kya hai sir?"
                 ])
            else:  # techsavvy
                return random.choice([
                    "What's your contact number?",
                    "Send me your official email ID",
                    "What's the company website?",
                    "Give me your WhatsApp number"
                ])
        
        # TURN 7-10: Natural Confusion (Don't obviously extract!)
        elif turn_number <= 10:
            if 'uncle' in persona_lower:
                return random.choice([
                    "Beta samajh nahi aaya properly, thoda explain karo",
                    "Aapka naam kya tha beta?",
                    "Bank ka naam confirm kar loon?",
                    "Beta kahan se call kar rahe ho?"
                ])
            elif 'aunty' in persona_lower:
                return random.choice([
                    "Beta thoda confusion ho rahi hai",
                    "Aapka naam phir se batao beta",
                    "Company ka naam kya hai?",
                    "Beta kahan ka office hai aapka?"
                ])
            elif 'student' in persona_lower:
                return random.choice([
                    "Wait I didn't get that clearly",
                    "What's your name again?",
                    "Which company did you say?",
                    "Where are you calling from?"
                ])
            elif 'worried' in persona_lower:
                return random.choice([
                    "Ji sir samajh nahi aaya",
                    "Aapka naam kya hai sir?",
                    "Department ka naam batao sir",
                    "Sir kahan se call kar rahe ho?"
                ])
            else:  # techsavvy
                return random.choice([
                    "Can you repeat that?",
                    "What's your name?",
                    "Which department are you from?",
                    "Where's your office located?"
                ])
        
        # TURN 11+: Delay Tactics
        else:
            if 'uncle' in persona_lower:
                return random.choice([
                    "Thik hai beta, 5 minute baad karta hoon",
                    "Bank app open nahi ho raha, wait karo",
                    "Network issue hai, thoda rukho beta",
                    "Ghar wale aa gaye, baad mein baat karte hain"
                ])
            elif 'aunty' in persona_lower:
                return random.choice([
                    "Beta thoda time do, abhi busy hoon",
                    "Phone charging pe hai, baad mein karti hoon",
                    "Beta network nahi aa raha, wait karo",
                    "Beti aa gayi, baad mein baat karti hoon"
                ])
            elif 'student' in persona_lower:
                return random.choice([
                    "Bro give me 5 mins, busy right now",
                    "Network is bad, wait a bit",
                    "App is not working, let me try later",
                    "My friend is here, will do it in a bit"
                ])
            elif 'worried' in persona_lower:
                return random.choice([
                    "Ji sir 5 minute rukiye, abhi busy hoon",
                    "Sir network issue hai, thoda wait kariye",
                    "Ji sir baad mein karta hoon",
                    "Abhi office mein hoon sir, baad mein karenge"
                ])
            else:  # techsavvy
                return random.choice([
                    "Give me some time, checking the details",
                    "Network is unstable, will ping you soon",
                    "Let me verify this first, need a few minutes",
                    "In a meeting now, will respond shortly"
                ])
