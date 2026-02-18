"""
Intelligence Analyst Agent — dedicated sub-agent for real-time intelligence extraction.

Runs in parallel with the persona agent on every turn. Analyzes scammer messages
for extractable intelligence and produces a structured INTELLIGENCE_LOG.

Responsibilities:
1. Extract UPI IDs, phone numbers, bank accounts, phishing links, emails, names
2. Use regex patterns (fast) + LLM-assisted extraction (for non-standard formats)
3. Produce a structured INTELLIGENCE_LOG dict every turn
4. Identify what the scammer is asking for (OTP, Aadhaar, PAN, etc.)
5. Suggest what fake data to provide if scammer asks for personal info
"""
import logging
import asyncio
import re
from typing import Dict, List, Optional, Any
from app.utils import patterns
from app.utils.dummy_data_generator import DummyDataGenerator

logger = logging.getLogger(__name__)


class IntelligenceAnalystAgent:
    """
    Dedicated intelligence extraction sub-agent.
    
    Runs alongside the persona agent to analyze every scammer message
    and produce structured intelligence logs.
    """

    # Keywords that indicate scammer is asking for personal data
    PERSONAL_DATA_REQUESTS = {
        "otp": ["otp", "one time password", "verification code", "code bhejo", "code send"],
        "aadhaar": ["aadhaar", "aadhar", "uid number", "aadhaar number"],
        "pan": ["pan card", "pan number", "permanent account number"],
        "bank_account": ["account number", "bank account", "acc number", "account no"],
        "upi": ["upi id", "gpay id", "phonepe id", "paytm id", "send to upi"],
        "cvv": ["cvv", "card verification", "3 digit", "back of card"],
        "pin": ["atm pin", "debit pin", "net banking pin", "mpin"],
        "password": ["password", "login password", "net banking password"],
    }

    # Scammer tactics to identify
    SCAMMER_TACTICS = {
        "urgency": ["immediately", "urgent", "asap", "right now", "within minutes", "deadline", "expires"],
        "threat": ["arrest", "block", "freeze", "legal action", "police", "court", "fir"],
        "authority": ["rbi", "cbi", "police", "government", "bank manager", "officer", "department"],
        "reward": ["won", "prize", "lottery", "congratulations", "selected", "reward", "cashback"],
        "fear": ["compromised", "hacked", "suspicious", "fraud detected", "unauthorized"],
    }

    def __init__(self):
        self.dummy_generator = DummyDataGenerator()
        self._groq_client = None

    def _get_groq_client(self):
        """Lazy-load Groq client."""
        if self._groq_client is None:
            try:
                from app.utils.groq_client import GroqClient
                import os
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    self._groq_client = GroqClient(api_key=api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Groq client for analyst: {e}")
        return self._groq_client

    def analyze_regex(self, message: str) -> Dict[str, List[str]]:
        """
        Fast regex-based extraction.
        
        Returns dict with all extracted items.
        """
        extracted = {
            "upi_ids": list(patterns.extract_upi_ids(message)),
            "phone_numbers": list(patterns.extract_phone_numbers(message)),
            "bank_accounts": list(patterns.extract_bank_accounts(message)),
            "urls": list(patterns.extract_urls(message)),
            "emails": list(patterns.extract_emails(message)),
            "names": list(patterns.extract_names(message)),
            "employee_ids": list(patterns.extract_employee_ids(message)),
        }
        return extracted

    def detect_data_requests(self, message: str) -> List[str]:
        """
        Detect what personal data the scammer is requesting from the victim.
        
        Returns list of data types being requested.
        """
        message_lower = message.lower()
        requested = []
        for data_type, keywords in self.PERSONAL_DATA_REQUESTS.items():
            if any(kw in message_lower for kw in keywords):
                requested.append(data_type)
        return requested

    def detect_tactics(self, message: str) -> List[str]:
        """
        Detect scammer tactics being used.
        
        Returns list of tactic names.
        """
        message_lower = message.lower()
        tactics = []
        for tactic, keywords in self.SCAMMER_TACTICS.items():
            if any(kw in message_lower for kw in keywords):
                tactics.append(tactic)
        return tactics

    async def llm_extract(self, message: str) -> Dict[str, List[str]]:
        """
        LLM-assisted extraction for non-standard formats.
        Only called when regex finds nothing significant.
        
        Returns dict with extracted items (may be empty).
        """
        client = self._get_groq_client()
        if not client:
            return {}

        system_prompt = """You are an intelligence extraction specialist analyzing scam messages.
Extract ONLY explicitly mentioned identifiers. Return JSON only.

Extract these if present:
- upi_ids: UPI payment IDs (format: name@bank or similar)
- phone_numbers: Indian phone numbers (10 digits, may have +91)
- bank_accounts: Bank account numbers (9-18 digits)
- emails: Email addresses
- names: Person names mentioned (scammer's name, company name)
- urls: Any URLs or website links

Return ONLY valid JSON like:
{"upi_ids": [], "phone_numbers": [], "bank_accounts": [], "emails": [], "names": [], "urls": []}

If nothing found, return empty lists. DO NOT invent data."""

        try:
            response = await asyncio.wait_for(
                client.generate_response(
                    system_prompt=system_prompt,
                    user_message=f"Extract from: {message}",
                    temperature=0.1,
                    max_tokens=200
                ),
                timeout=2.0  # Very short timeout — this is supplementary
            )
            import json
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception as e:
            logger.debug(f"LLM extraction skipped: {e}")

        return {}

    async def analyze(
        self,
        message: str,
        turn_number: int,
        scam_type: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Full analysis of a scammer message.
        
        Args:
            message: Scammer's message text
            turn_number: Current conversation turn
            scam_type: Detected scam type
            conversation_history: Previous messages
            
        Returns:
            INTELLIGENCE_LOG dict with all extracted data and analysis
        """
        logger.info(f"[IntelligenceAnalyst] Analyzing turn {turn_number}: {message[:60]}...")

        # Step 1: Fast regex extraction
        regex_extracted = self.analyze_regex(message)

        # Step 2: Check if regex found anything significant
        has_significant_intel = any([
            regex_extracted["upi_ids"],
            regex_extracted["phone_numbers"],
            regex_extracted["bank_accounts"],
            regex_extracted["urls"],
            regex_extracted["emails"],
        ])

        # Step 3: LLM extraction only if regex found nothing (save latency)
        llm_extracted = {}
        if not has_significant_intel and turn_number > 1:
            try:
                llm_extracted = await self.llm_extract(message)
            except Exception:
                pass

        # Step 4: Merge results (regex takes priority, LLM fills gaps)
        merged = {
            "upi_ids": list(set(regex_extracted.get("upi_ids", []) + llm_extracted.get("upi_ids", []))),
            "phone_numbers": list(set(regex_extracted.get("phone_numbers", []) + llm_extracted.get("phone_numbers", []))),
            "bank_accounts": list(set(regex_extracted.get("bank_accounts", []) + llm_extracted.get("bank_accounts", []))),
            "urls": list(set(regex_extracted.get("urls", []) + llm_extracted.get("urls", []))),
            "emails": list(set(regex_extracted.get("emails", []) + llm_extracted.get("emails", []))),
            "names": list(set(regex_extracted.get("names", []) + llm_extracted.get("names", []))),
            "employee_ids": regex_extracted.get("employee_ids", []),
        }

        # Step 5: Detect what scammer is requesting
        data_requests = self.detect_data_requests(message)

        # Step 6: Detect scammer tactics
        tactics = self.detect_tactics(message)

        # Step 7: Generate fake data suggestions for requested items
        fake_data_suggestions = {}
        for req_type in data_requests:
            if req_type not in ["otp", "cvv", "pin", "password"]:  # Never provide these
                suggestion = self.dummy_generator.get_response_for_request(req_type)
                if suggestion.get("fake_value"):
                    fake_data_suggestions[req_type] = suggestion["fake_value"]

        # Step 8: Count total intelligence items
        total_items = sum(len(v) for v in merged.values() if isinstance(v, list))

        # Build INTELLIGENCE_LOG
        intelligence_log = {
            "turn": turn_number,
            "scam_type": scam_type or "unknown",
            "extracted": {k: v for k, v in merged.items() if v},  # Only non-empty
            "total_items_found": total_items,
            "scammer_requesting": data_requests,
            "tactics_detected": tactics,
            "fake_data_available": fake_data_suggestions,
            "extraction_method": "llm+regex" if llm_extracted else "regex",
        }

        logger.info(f"[INTELLIGENCE_LOG] Turn {turn_number}: {total_items} items extracted, "
                    f"tactics={tactics}, requests={data_requests}")

        if merged["upi_ids"]:
            logger.info(f"  🎯 UPI IDs: {merged['upi_ids']}")
        if merged["phone_numbers"]:
            logger.info(f"  📞 Phones: {merged['phone_numbers']}")
        if merged["bank_accounts"]:
            logger.info(f"  🏦 Accounts: {merged['bank_accounts']}")
        if merged["urls"]:
            logger.info(f"  🔗 URLs: {merged['urls']}")
        if merged["emails"]:
            logger.info(f"  📧 Emails: {merged['emails']}")

        return intelligence_log

    def analyze_sync(
        self,
        message: str,
        turn_number: int,
        scam_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version for use in non-async contexts.
        Uses regex only (no LLM).
        """
        regex_extracted = self.analyze_regex(message)
        data_requests = self.detect_data_requests(message)
        tactics = self.detect_tactics(message)

        total_items = sum(len(v) for v in regex_extracted.values() if isinstance(v, list))

        return {
            "turn": turn_number,
            "scam_type": scam_type or "unknown",
            "extracted": {k: v for k, v in regex_extracted.items() if v},
            "total_items_found": total_items,
            "scammer_requesting": data_requests,
            "tactics_detected": tactics,
            "fake_data_available": {},
            "extraction_method": "regex_only",
        }


# Global instance
intelligence_analyst = IntelligenceAnalystAgent()
