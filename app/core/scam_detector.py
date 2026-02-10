from app.models.intelligence import ScamDetection
from app.utils.llm_client import llm_client
from app.core.scam_classifier_enhanced import enhanced_classifier
from langchain_core.messages import SystemMessage, HumanMessage
import logging
import re

logger = logging.getLogger(__name__)


class ScamDetector:
    """
    detects scam intent using a Hybrid Pipeline:
    1. Strict Keyword Matching (Microseconds) - For obvious scams.
    2. Safe Pattern Matching (Microseconds) - For obvious safe messages.
    3. LLM Verification (Sub-second via Groq) - For ambiguous cases.
    """
    
    def __init__(self):
        self.safe_patterns = [
            r"^(hi|hello|hey|good morning|good evening|good afternoon|sup|yo)[.!]?$",
            r"^(hi|hello|hey)[,]? (how are you|how do you do|what's up)\??$",
            r"^who are you\??$",
            r"^nice to meet you[.]?$",
            r"^how are you\??$",
            r"^safe$", # For testing
            r"^government advisory.*",  # Ignore official warnings
            r"^cybercrime.*", # Official cybercrime warnings
            r".*received.*from.*@upi.*", # UPI money RECEIVED is always safe
            r".*credited.*to.*a/c.*", # Bank credits are safe
        ]

    async def detect(self, message_text: str, conversation_history: list = None) -> ScamDetection:
        """
        Detect if a message is a scam using the hybrid pipeline.
        """
        try:
            # Stage 1: Check for Safe Patterns (Instant Ignore)
            if self._is_safe_message(message_text):
                return ScamDetection(
                    is_scam=False, 
                    confidence=1.0, 
                    scam_type="unknown", 
                    recommended_agent="uncle", 
                    reasoning="Matched safe greeting pattern"
                )

            # Stage 2: Enhanced Keyword Classifier (Instant Scam Detect)
            enhanced_type, enhanced_persona, enhanced_conf = enhanced_classifier.classify(message_text)
            
            # If high confidence keyword match (>0.7), return immediately
            if enhanced_conf >= 0.7:
                 return ScamDetection(
                    is_scam=enhanced_type != "unknown",
                    confidence=enhanced_conf,
                    scam_type=enhanced_type,
                    recommended_agent=enhanced_persona,
                    reasoning=f"High confidence keyword match: {enhanced_type}"
                )

            # Stage 3: LLM Verification (Groq/Fast LLM)
            # Only reached if message is ambiguous
            logger.info("🤔 Message ambiguous. Verifying with LLM...")
            return await self._llm_classify_scam(message_text)
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            # Fail safe
            return ScamDetection(is_scam=False, confidence=0.0, scam_type="unknown", recommended_agent="uncle", reasoning="Error")

    def _is_safe_message(self, text: str) -> bool:
        """Check if message is a generic safe greeting."""
        clean_text = text.strip().lower()
        for pattern in self.safe_patterns:
            if re.match(pattern, clean_text):
                return True
        return False

    async def _llm_classify_scam(self, text: str) -> ScamDetection:
        """
        Ask the LLM to classify the message.
        Expected latency: < 1s with Groq Llama-3.3-70b
        """
        system_prompt = """You are a scam detection expert. Analyze the user's message.
        
        Output format (JSON only):
        {
            "is_scam": boolean,
            "confidence": float (0.0-1.0),
            "scam_type": "string" (one of: bank_fraud, upi_fraud, investment, job_offer, legal_threat, authority_impersonation, lottery, phishing, unknown),
            "reasoning": "short explanation"
        }
        
        Rules:
        1. SCAM: Asking for money/OTP/bank details/clicking links from UNKNOWN/OFFICIAL-LOOKING sources.
        2. SCAM: "Digital Arrest", "Customs Duty", "Lottery", "Easy Job with UPFRONT FEE", "Crypto Returns".
        3. SCAM if job offer asks for PAYMENT (training fee, verification fee, etc.).
        4. SCAM: "Virtual Arrest" or "Video Inquiry" is ALWAYS SCAM (Real police/CBI do not do video calls).
        5. SCAM: "Money Received" + "Return via Link" is ALWAYS SCAM (Real refunds don't need links).
        6. SAFE: Standard bank ALERTS (Credited/Debited/Bill Due) without suspicious links.
        7. SAFE: Transactions RECEIVED (Money coming IN is safe) WITHOUT asking to return it.
        8. SAFE: Personal messages from known contacts (Mom, Dad, Brother) asking for small amounts/groceries.
        9. SAFE: Legitimate interview invitations from KNOWN companies (TCS, Infosys, Wipro) WITHOUT asking for money.
        10. SAFE: Normal conversation ("How are you?", "Tell me a joke").
        11. If unsure -> confidence < 0.5.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=text)
        ]

        try:
            # 1. Try Gemini First (Primary - Higher Intelligence)
            try:
                from app.utils.llm_client import GeminiLLMClient
                gemini_client = GeminiLLMClient()
                if gemini_client.api_key:
                    logger.info("🤖 Verifying with Gemini 1.5 Pro...")
                    response_text = await gemini_client.ainvoke(messages)
                    if response_text:
                         return self._parse_llm_response(response_text)
            except Exception as e:
                logger.warning(f"⚠️ Gemini detection failed: {e}. Falling back to Groq...")

            # 2. Fallback to Groq (Fast & Reliable)
            logger.info("⚡ Verifying with Groq Llama-3...")
            response_text = await llm_client.ainvoke(messages)
            return self._parse_llm_response(response_text)
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return ScamDetection(is_scam=False, confidence=0.0, scam_type="unknown", recommended_agent="uncle", reasoning="Error")

    def _parse_llm_response(self, response_text: str) -> ScamDetection:
        """Helper to parse LLM JSON response."""
        try:
            # Parse JSON from response
            import json
            # Extract JSON block if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                 response_text = response_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(response_text)
            
            # Map detection to persona
            raw_type = data.get("scam_type", "unknown")
            
            # Comprehensive Normalization map
            type_map = {
                "lottery": "prize_lottery", "prize": "prize_lottery", "winning": "prize_lottery", "reward": "prize_lottery",
                "job": "job_offer", "employment": "job_offer", "work": "job_offer", "career": "job_offer",
                "bank": "bank_fraud", "banking": "bank_fraud", "account": "bank_fraud",
                "card": "credit_card", "credit_card": "credit_card", "debit": "credit_card",
                "upi": "upi_scam", "payment": "upi_scam", "gpay": "upi_scam", "phonepe": "upi_scam", "paytm": "upi_scam",
                "police": "police_legal", "arrest": "police_legal", "legal": "police_legal", "law": "police_legal", "court": "police_legal", "authority": "authority_impersonation",
                "tax": "tax_refund", "refund": "tax_refund", "aadhaar": "tax_refund",
                "government": "govt_scheme", "govt": "govt_scheme", "scheme": "govt_scheme",
                "bill": "bill_payment", "electricity": "bill_payment", "utility": "bill_payment",
                "investment": "investment", "crypto": "investment", "trading": "investment", "stock": "investment",
                "romance": "romance", "dating": "romance", "relationship": "romance", "friendship": "romance", "social": "romance",
                "delivery": "delivery", "package": "delivery", "parcel": "delivery", "courier": "delivery",
                "phishing": "phishing", "link": "phishing", "click": "phishing"
            }
            
            scam_type = type_map.get(raw_type, raw_type)
            
            persona_map = {
                "bank_fraud": "uncle", "upi_fraud": "uncle", "phishing": "uncle",
                "authority_impersonation": "worried", "legal_threat": "worried", "police_legal": "worried",
                "investment": "techsavvy", "job_offer": "techsavvy",
                "prize_lottery": "uncle", "bill_payment": "uncle",
                "unknown": "uncle"
            }
            
            return ScamDetection(
                is_scam=data.get("is_scam", False),
                confidence=data.get("confidence", 0.0),
                scam_type=scam_type,
                recommended_agent=persona_map.get(scam_type, "uncle"),
                reasoning=data.get("reasoning", "LLM Analysis")
            )
        except Exception as e:
            logger.error(f"JSON Parsing failed: {e}")
            return ScamDetection(is_scam=False, confidence=0.0, scam_type="unknown", recommended_agent="uncle", reasoning="Parse Error")

