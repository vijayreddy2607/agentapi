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
    
    # ── AGGRESSIVE 10-TURN EXTRACTION STRATEGY ──────────────────────────────────
    # GUVI sends only 10 messages. We MUST extract as many intel categories
    # as possible within those 10 turns. Each turn targets a specific data type.
    # Turn 1 → phone/employee ID, Turn 2 → UPI ID, Turn 3 → bank account,
    # Turn 4 → email, Turn 5 → phishing link, Turn 6-7 → case/policy IDs,
    # Turn 8-10 → cross-confirm + overflow.
    TURN_STRATEGIES = {
        # ── TURN 1: React + ask for official contact number & employee ID ──────
        "1": {
            "name": "REACT + PHONE EXTRACTION",
            "target": "phone_number + employee_ID",
            "instructions": """
You just received a scam message. React naturally (scared/excited/confused) then IMMEDIATELY ask:
→ "What is your official contact number and employee ID?"
→ OR: "Which department are you from? What is your employee ID number?"
You MUST ask for THEIR phone number and employee ID in your very first response.
Keep it short (1-2 sentences). End with a question asking for their number or ID."""
        },
        # ── TURN 2: Ask for UPI ID / payment account ──────────────────────────
        "2": {
            "name": "UPI ID + PAYMENT DETAILS EXTRACTION",
            "target": "upi_id + bank_account",
            "instructions": """
ASK FOR THEIR UPI ID or bank account number right now.
→ "Okay, what is your UPI ID or bank account where I should send the verification?"
→ OR: "Which UPI app should I use? What is the UPI ID or account number?"
→ OR: "Please give me your UPI ID or bank account to confirm payment."
You MUST ask for a UPI ID or bank account number. Make it sound natural."""
        },
        # ── TURN 3: Ask for bank account number explicitly ─────────────────────
        "3": {
            "name": "BANK ACCOUNT EXTRACTION",
            "target": "bank_account + IFSC",
            "instructions": """
ASK FOR THEIR BANK ACCOUNT NUMBER AND IFSC CODE.
→ "What is the bank account number and IFSC code I should use?"
→ OR: "Which branch? Please give me the account number and bank IFSC."
→ OR: "I want to transfer — what is the exact account number and bank name?"
You MUST ask for a bank account number. Be polite but persistent."""
        },
        # ── TURN 4: Ask for email address ─────────────────────────────────────
        "4": {
            "name": "EMAIL + IDENTITY EXTRACTION",
            "target": "email_address + name",
            "instructions": """
ASK FOR THEIR OFFICIAL EMAIL ADDRESS AND FULL NAME.
→ "What is your official company email ID? I will send my details by email."
→ OR: "Please give me your email address so I can verify this is official."
→ OR: "What email should I contact you at? And your full name please?"
You MUST ask for their email address in this response."""
        },
        # ── TURN 5: Ask for website / phishing link ────────────────────────────
        "5": {
            "name": "WEBSITE LINK EXTRACTION",
            "target": "phishing_link + url",
            "instructions": """
ASK FOR THE WEBSITE LINK OR PORTAL URL.
→ "What is the official website link where I can verify this?"
→ OR: "Please send me the portal URL or link so I can check myself."
→ OR: "What website should I open? Can you share the link?"
You MUST ask for a website URL or link in this response."""
        },
        # ── TURN 6: Ask for case/reference/ticket ID ───────────────────────────
        "6": {
            "name": "CASE ID + REFERENCE EXTRACTION",
            "target": "case_id + reference_number",
            "instructions": """
ASK FOR THE CASE/REFERENCE/TICKET/POLICY NUMBER.
→ "What is the case reference ID or ticket number for my complaint?"
→ OR: "Can you give me the reference number or case ID for this transaction?"
→ OR: "What is my policy number or order number you are calling about?"
You MUST ask for a case ID, reference number, policy or order number."""
        },
        # ── TURN 7: Confirm all — re-ask any missing details — CASE ID PRIORITY ─
        "7": {
            "name": "CASE ID + OVERFLOW EXTRACTION",
            "target": "case_id + any_missing_intel",
            "instructions": """
If scammer has NOT given a case ID / reference number yet, ASK FOR IT NOW.
→ "What is the case reference ID or complaint number for this issue?"
→ OR: "Can you give me the exact ticket or case number so I can file a report?"
→ OR: "Before I do anything, I need the official case or reference ID — what is it?"
If already have case ID, ask them to CONFIRM/REPEAT any missing intel:
→ "I need to double-check — your phone number again? And the bank account?"
CASE ID is the priority target this turn if not yet collected."""
        },
        # ── TURNS 8-10: Stall + re-confirm any remaining gaps ────────────────────
        "8+": {
            "name": "STALL + FINAL EXTRACTION",
            "target": "re-confirm + case_id + stall",
            "instructions": """
Stall while re-asking for any MISSING intel (check INTELLIGENCE STATUS above).
→ If no case ID: "Sorry, I lost my notes — what was the case or reference number?"
→ If no phone: "What is your direct callback number again?"
→ If no UPI: "What UPI ID should the verification payment go to?"
Always refer to INTELLIGENCE STATUS above to pick the right missing item.
Keep them engaged. Re-ask name, employee ID, case number, or phone."""
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
        """Get aggressive per-turn extraction strategy (optimized for 10-turn GUVI sessions)."""
        strategies = {
            1: self.TURN_STRATEGIES["1"],
            2: self.TURN_STRATEGIES["2"],
            3: self.TURN_STRATEGIES["3"],
            4: self.TURN_STRATEGIES["4"],
            5: self.TURN_STRATEGIES["5"],
            6: self.TURN_STRATEGIES["6"],
            7: self.TURN_STRATEGIES["7"],
        }
        return strategies.get(turn_number, self.TURN_STRATEGIES["8+"])
    
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

    def build_system_prompt(self, persona: str, turn_number: int, scam_type: Optional[str] = None, extracted_intel: Optional[dict] = None) -> str:
        """Build system prompt — aggressive extraction directive layered on top of persona."""
        turn_strategy = self.get_turn_strategy(turn_number)

        # Normalize persona name to canonical key
        persona_key = self.PERSONA_ALIASES.get(persona.lower(), "uncle_persona")
        base_prompt = self.ENHANCED_PERSONA_PROMPTS[persona_key]

        # Persona-aware language rule
        hinglish_ok = persona_key in {"uncle_persona", "aunty_persona"}
        if hinglish_ok:
            language_rule = (
                "🌐 LANGUAGE RULE:\n"
                "- Use natural Hinglish (mix of Hindi and English) as your persona would.\n"
                "- Be warm, conversational — short sentences only.\n"
            )
        else:
            language_rule = (
                "🌐 LANGUAGE RULE:\n"
                "- RESPOND IN ENGLISH ONLY. Do NOT use Hindi or Hinglish.\n"
                "- All words must be English.\n"
            )

        # ── INTEL STATUS BLOCK ────────────────────────────────────────────────
        # Summarise what's already captured and what's still missing.
        # This prevents the LLM from asking for things already extracted.
        intel_status_block = ""
        if extracted_intel:
            already = []
            missing = []
            fields = [
                ("phoneNumbers",   "phone number"),
                ("upiIds",         "UPI ID"),
                ("bankAccounts",   "bank account"),
                ("emailAddresses", "email address"),
                ("phishingLinks",  "phishing link/URL"),
                ("caseIds",        "case/reference ID"),
            ]
            for field_key, label in fields:
                values = extracted_intel.get(field_key)
                if values:
                    first_val = values[0] if isinstance(values, list) else next(iter(values), "")
                    already.append(f"✅ {label}: {first_val}")
                else:
                    missing.append(f"❌ {label}")

            intel_status_block = (
                "\n📊 INTELLIGENCE STATUS:\n"
                + ("  ALREADY EXTRACTED: " + ", ".join(already) + "\n" if already else "  Nothing extracted yet.\n")
                + ("  STILL MISSING — ASK NOW: " + ", ".join(missing) if missing else "  ✔ All primary fields extracted!")
                + "\n"
            )

        # ── MANDATORY EXTRACTION DIRECTIVE ───────────────────────────────────
        # This overrides the base persona prompt's casualness.
        # GUVI only gives 10 turns — we MUST extract a different data type each turn.
        extraction_target = turn_strategy.get("target", "any_intel")
        extraction_directive = (
            f"{intel_status_block}"
            f"\n⚡ MANDATORY THIS TURN (Turn {turn_number}) — TARGET: {extraction_target}\n"
            f"{turn_strategy['instructions'].strip()}\n"
            "\nRULE: Your response MUST contain a direct question asking for the above target.\n"
            "If scammer already shared it, ACKNOWLEDGE then ask for the NEXT missing item\n"
            "(e.g., if they gave phone, now ask for UPI ID or bank account).\n"
        )

        system_prompt = (
            f"{base_prompt}\n\n"
            f"🎯 CURRENT PHASE: {turn_strategy['name']} (Turn {turn_number})\n"
            f"{extraction_directive}\n"
            f"{language_rule}\n"
            "🚨 SECURITY RULES:\n"
            "- NEVER share OTP/PIN/CVV numbers\n"
            "- If asked for OTP → stall and ask their name/number/ID instead\n"
            "- Keep response under 150 characters, 1-2 sentences max\n"
            "- Always end with a question to keep the scammer responding"
        )
        return system_prompt


    
    async def generate_response(
        self,
        persona: str,
        scammer_message: str,
        turn_number: int,
        conversation_history: Optional[List[Dict]] = None,
        scam_type: Optional[str] = None,
        extracted_intel: Optional[dict] = None
    ) -> str:
        """
        Generate a contextual response using LLM.
        
        Args:
            persona: Persona to use
            scammer_message: Latest message from scammer
            turn_number: Current turn number
            conversation_history: Previous conversation (optional)
            scam_type: Type of scam detected (optional)
            extracted_intel: Dict of already-extracted intelligence (optional)
            
        Returns:
            Generated response text
        """
        logger.info(f"Generating response for {persona}, turn {turn_number}")
        
        # Build system prompt with templates and strategy
        system_prompt = self.build_system_prompt(persona, turn_number, scam_type, extracted_intel)
        
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
            
            # CRITICAL: Keep total response < 5s for competition
            # 4.8s timeout leaves buffer for scam detection + processing
            import asyncio
            response = await asyncio.wait_for(
                self.llm_client.generate_response(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    temperature=temperature,
                    max_tokens=60  # 60 tokens ≈ 45 words — forces short human-like messages
                ),
                timeout=4.8
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
                # NOTE: ALL responses must be English — Hinglish will be rejected by the language gate
                if 'uncle' in persona.lower():
                    denials = [
                        "I will share it, but first please give me your employee ID and contact number?",
                        "Okay I'll do it, but what is your official phone number and email address?",
                        "I can help with that, but first tell me your employee ID and website link?",
                        "Sure, but please give me your customer care number first for verification.",
                        "I will send it, but I need your official contact details and employee ID first."
                    ]
                elif 'aunty' in persona.lower():
                    denials = [
                        "I will help you beta, but first give me your name and contact number please?",
                        "Okay, but what is your WhatsApp number and official email for confirmation?",
                        "I can do that, but please send me your website link and employee ID first.",
                        "Sure, but give me your office phone number for verification first please?"
                    ]
                elif 'student' in persona.lower():
                    denials = [
                        "Sure bro I'll send it, but first what's your number and employee ID?",
                        "OK I'll do it, but what's your WhatsApp number and website link?",
                        "Yeah I'll send it, but first give me your official email and number.",
                        "Alright I'll share it, but need your contact details for verification first."
                    ]
                else:
                    denials = [
                        "I will send it, but please give me your phone number and website link first.",
                        "Sure, but what is your official WhatsApp number for me to contact you?",
                        "I can share it, but first please provide your official contact details."
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
        
        # ALL STRINGS BELOW MUST BE ENGLISH ONLY — Hinglish responses are rejected by the
        # is_english_response() gate in BaseAgent and replaced by a worse generic fallback.

        # TURN 1-3: Build Trust / Show Confusion
        if turn_number <= 3:
            if 'uncle' in persona_lower:
                return random.choice([
                    "Oh my! What is happening? Which department are you calling from? Please explain.",
                    "I am confused beta. Can you tell me again slowly — who is calling and why?",
                    "What? I don't understand! Which bank or company is this call from?"
                ])
            elif 'aunty' in persona_lower:
                return random.choice([
                    "Oh dear, I don't understand. Which company are you calling from?",
                    "Can you explain again slowly? I am a little confused by what you are saying.",
                    "What is happening? Please tell me again — who is calling and from where?"
                ])
            elif 'student' in persona_lower:
                return random.choice([
                    "Wait what? Can you explain that again?",
                    "Confused bro, what do you mean exactly?",
                    "Hold on, what's happening here? Who are you?"
                ])
            elif 'worried' in persona_lower:
                return random.choice([
                    "Oh no, I did not understand. Which organization are you calling from?",
                    "I am scared and confused. Can you explain what happened clearly?",
                    "Please explain again — which bank or department is this?"
                ])
            else:  # techsavvy
                return random.choice([
                    "Hold on, I didn't catch that. Which company are you from?",
                    "Can you clarify what you need? Please send your official credentials.",
                    "I'm not following. Explain again — who are you and what's your employee ID?"
                ])
        
        # TURN 4-6: Extract Contact Info
        elif turn_number <= 6:
            if 'uncle' in persona_lower:
                return random.choice([
                    "Okay, but first — what is your official phone number and employee ID?",
                    "I see. What is your WhatsApp number and company email address?",
                    "Please give me your official contact number and website link for verification.",
                    "Before I proceed, what is your direct phone number and email address?"
                ])
            elif 'aunty' in persona_lower:
                return random.choice([
                    "Okay dear, but first give me your phone number and name please?",
                    "I need your WhatsApp number and email address for confirmation, please.",
                    "Please share your official website link and contact number first.",
                    "What is your office phone number? I want to verify before doing anything."
                ])
            elif 'student' in persona_lower:
                return random.choice([
                    "OK but what's your number first? I need to verify you.",
                    "Sure, but send me your WhatsApp number and employee ID.",
                    "What's your email ID and official website link?",
                    "Send me the website link so I can check this is legit."
                ])
            elif 'worried' in persona_lower:
                return random.choice([
                    "Please give me your official phone number sir. I need to verify.",
                    "What is your email address? I want to confirm this is real.",
                    "What is the office contact number and website I can check?",
                    "Please give me the official website address for my records."
                ])
            else:  # techsavvy
                return random.choice([
                    "What's your official contact number and company email?",
                    "Send me your official email ID and employee badge number.",
                    "What's the company website URL? I will verify on WHOIS.",
                    "Give me your direct phone number so I can call back the official number."
                ])
        
        # TURN 7-10: Re-confirm missing intel
        elif turn_number <= 10:
            if 'uncle' in persona_lower:
                return random.choice([
                    "I did not catch that properly. What was your employee ID number again?",
                    "I am writing everything down — what is your name and case reference number?",
                    "Please confirm — which bank account should I use and what is the IFSC code?",
                    "I need to verify — what is the official case or complaint reference ID?"
                ])
            elif 'aunty' in persona_lower:
                return random.choice([
                    "I am a little confused dear. What was your name and contact number again?",
                    "Can you repeat the case reference number? I want to write it down.",
                    "Which company are you from again? And the phone number?",
                    "What is the official reference ID or ticket number for this?"
                ])
            elif 'student' in persona_lower:
                return random.choice([
                    "Wait I didn't get that clearly. What's your employee ID again?",
                    "What's your name and which company are you from?",
                    "Can you send me the reference or order number for this?",
                    "Where exactly are you calling from and what's the ticket ID?"
                ])
            elif 'worried' in persona_lower:
                return random.choice([
                    "Sorry sir, I didn't understand. What is the case reference ID?",
                    "I need the complaint number sir. What is the official case ID?",
                    "Please give me the ticket or reference number before I do anything.",
                    "What is your full name and the official case or complaint number?"
                ])
            else:  # techsavvy
                return random.choice([
                    "Can you repeat that? What is your employee ID and case reference?",
                    "What's your name and which department are you calling from?",
                    "I need the official case or ticket number — what is it?",
                    "Where is your office and what is the reference ID for this issue?"
                ])
        
        # TURN 11+: Delay Tactics (English only!)
        else:
            if 'uncle' in persona_lower:
                return random.choice([
                    "Okay, please wait 5 minutes. I need to find my reading glasses.",
                    "The bank app is not opening for me. Can you wait a moment?",
                    "My internet is very slow today. Please hold for a few minutes.",
                    "Someone is at the door. Please hold on — I will be back."
                ])
            elif 'aunty' in persona_lower:
                return random.choice([
                    "Dear please give me a moment. I am doing something in the kitchen.",
                    "My phone battery is very low. Can you please wait a few minutes?",
                    "The internet is not working properly. Please hold on.",
                    "My daughter just came home. Can you call back in 5 minutes?"
                ])
            elif 'student' in persona_lower:
                return random.choice([
                    "Bro give me 5 mins, I'm busy right now.",
                    "Network is really bad, wait a bit.",
                    "App is crashing, let me try again in a minute.",
                    "My friend just arrived, can we continue in a bit?"
                ])
            elif 'worried' in persona_lower:
                return random.choice([
                    "Please give me 5 minutes sir. I need to check something first.",
                    "Sir there is a network issue on my side. Please wait.",
                    "I need to call my son first and confirm. Please hold.",
                    "I am not able to access the portal right now. Give me a moment."
                ])
            else:  # techsavvy
                return random.choice([
                    "Give me some time. I'm checking the IP and domain details.",
                    "Network is unstable on my end. Will get back to you shortly.",
                    "Let me verify your credentials first. Need a few minutes.",
                    "Currently in another call. Will respond in about 5 minutes."
                ])
