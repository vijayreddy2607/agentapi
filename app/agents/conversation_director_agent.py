"""
Conversation Director Agent — meta-orchestrator for the honeypot multi-agent system.

Responsibilities:
1. Select the optimal persona based on scam type and conversation phase
2. Monitor conversation quality and decide if persona should switch
3. Select the next extraction strategy (what to ask for next)
4. Decide when to stall vs. extract vs. build trust
5. Coordinate between persona agent and intelligence analyst

This agent runs BEFORE the persona agent on each turn.
"""
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class ConversationDirectorAgent:
    """
    Meta-orchestrator that directs the honeypot conversation strategy.
    
    Decides:
    - Which persona to use (and when to switch)
    - What extraction strategy to employ this turn
    - Whether to stall, extract, or build trust
    """

    # Scam type → best persona mapping (primary)
    SCAM_PERSONA_MAP = {
        "bank_kyc": "uncle",
        "upi_scam": "uncle",
        "credit_card": "worried",
        "investment": "techsavvy",
        "police_legal": "worried",
        "tax_refund": "worried",
        "govt_scheme": "uncle",
        "job_offer": "student",
        "prize_lottery": "aunty",
        "bill_payment": "worried",
        "romance": "aunty",
        "delivery": "worried",
        "urgency_threat": "worried",
        "unknown": "uncle",
    }

    # Fallback persona if primary doesn't engage well
    FALLBACK_PERSONA_MAP = {
        "uncle": "worried",
        "worried": "uncle",
        "aunty": "uncle",
        "student": "worried",
        "techsavvy": "uncle",
    }

    # Extraction strategy per phase
    PHASE_STRATEGIES = {
        "build_trust": {
            "name": "Build Trust",
            "description": "Appear naive and interested. Express appropriate emotion.",
            "extraction_targets": [],
            "max_turns": 3,
        },
        "extract_digital": {
            "name": "Extract Digital IDs",
            "description": "Ask for UPI ID, website link, email for 'verification'.",
            "extraction_targets": ["upi_id", "url", "email"],
            "max_turns": 3,
        },
        "extract_contact": {
            "name": "Extract Contact Info",
            "description": "Ask for phone number, WhatsApp, company name.",
            "extraction_targets": ["phone", "company_name", "name"],
            "max_turns": 3,
        },
        "extract_financial": {
            "name": "Extract Financial Details",
            "description": "Ask for bank account, IFSC, branch details.",
            "extraction_targets": ["bank_account", "ifsc"],
            "max_turns": 2,
        },
        "stall": {
            "name": "Strategic Stall",
            "description": "Waste time with excuses, delays, technical problems.",
            "extraction_targets": [],
            "max_turns": 999,
        },
    }

    # Phrases that indicate the scammer is REFUSING to share info
    REFUSAL_PATTERNS = [
        "cannot give", "can't give", "cant give",
        "cannot share", "can't share", "cant share",
        "not allowed", "not permitted", "not supposed to",
        "should not give", "should not share",
        "won't give", "wont give", "won't share", "wont share",
        "don't ask", "dont ask",
        "why do you need", "why are you asking",
        "just do it", "just proceed", "just follow",
        "focus on", "stop asking", "irrelevant",
        "my number is not required", "number is not needed",
        "not necessary", "no need for that",
        "security reasons", "policy", "confidential",
    ]

    # Pivot sequence when scammer refuses — try alternatives
    REFUSAL_PIVOT_SEQUENCE = [
        # If they won't give phone → ask for email
        {"refused": "phone", "pivot_to": "email",
         "pivot_hint": "Scammer refused phone. Ask for their email address or official ID instead."},
        # If they won't give email → ask for UPI/website
        {"refused": "email", "pivot_to": "upi_or_link",
         "pivot_hint": "Scammer refused email. Ask for their UPI ID or company website link."},
        # If they won't give UPI → ask for company name/employee ID
        {"refused": "upi_or_link", "pivot_to": "company_id",
         "pivot_hint": "Scammer refused link. Ask for their company name, branch, or employee ID."},
        # If they won't give anything → use suspicion stall
        {"refused": "company_id", "pivot_to": "stall_suspicion",
         "pivot_hint": "Scammer refuses all info. Raise gentle suspicion: 'If you can't give any details, how can I trust this?'"},
    ]

    def __init__(self):
        self._persona_engagement_scores: Dict[str, float] = {}

    def select_persona(
        self,
        scam_type: str,
        current_persona: Optional[str] = None,
        turn_number: int = 1,
        conversation_quality: float = 1.0
    ) -> Tuple[str, bool]:
        """
        Select the best persona for this conversation.
        
        Args:
            scam_type: Detected scam type
            current_persona: Currently active persona (if any)
            turn_number: Current turn number
            conversation_quality: 0-1 score of how well conversation is going
            
        Returns:
            Tuple of (persona_name, should_switch)
        """
        # First turn — always use primary persona for scam type
        if current_persona is None or turn_number == 1:
            persona = self.SCAM_PERSONA_MAP.get(scam_type, "uncle")
            logger.info(f"[Director] Turn {turn_number}: Selected primary persona '{persona}' for scam type '{scam_type}'")
            return persona, False

        # Check if we should switch persona (only after turn 5 if quality is poor)
        should_switch = False
        if turn_number > 5 and conversation_quality < 0.3:
            # Scammer may be losing interest — try a different persona
            fallback = self.FALLBACK_PERSONA_MAP.get(current_persona, "uncle")
            if fallback != current_persona:
                logger.info(f"[Director] Turn {turn_number}: Low quality ({conversation_quality:.2f}), "
                           f"switching from '{current_persona}' to '{fallback}'")
                return fallback, True

        # Keep current persona
        return current_persona, False

    def select_strategy(
        self,
        turn_number: int,
        extracted_so_far: Dict[str, List],
        scammer_requesting: List[str],
        scam_type: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Select the extraction strategy for this turn.
        
        Args:
            turn_number: Current turn number
            extracted_so_far: Intelligence already extracted
            scammer_requesting: What the scammer is asking for
            scam_type: Type of scam
            
        Returns:
            Strategy dict with name, description, and extraction_targets
        """
        # Count what we have
        has_upi = bool(extracted_so_far.get("upi_ids"))
        has_phone = bool(extracted_so_far.get("phone_numbers"))
        has_account = bool(extracted_so_far.get("bank_accounts"))
        has_url = bool(extracted_so_far.get("urls"))
        has_email = bool(extracted_so_far.get("emails"))
        has_case_id = bool(extracted_so_far.get("case_ids"))
        has_digital = has_upi or has_url or has_email  # got something digital already

        # Phase 1: Build trust (turn 1 ONLY — just react)
        if turn_number <= 1:
            strategy = self.PHASE_STRATEGIES["build_trust"].copy()
            strategy["priority"] = "establish_rapport"

        # Phase 2: Extract digital IDs (turns 2-4) — START EARLY
        elif turn_number <= 4:
            strategy = self.PHASE_STRATEGIES["extract_digital"].copy()
            if has_upi and has_url:
                # Already have digital IDs, move to contact
                strategy = self.PHASE_STRATEGIES["extract_contact"].copy()
            strategy["priority"] = "get_upi_or_link"

            # ── CIRCLE BACK to phone after getting email/UPI ──────────────────
            if has_digital and not has_phone:
                strategy["circle_back_phone"] = True

        # Phase 3: Extract contact info (turns 5-7)
        elif turn_number <= 7:
            strategy = self.PHASE_STRATEGIES["extract_contact"].copy()
            if has_phone:
                # Already have phone, try financial
                strategy = self.PHASE_STRATEGIES["extract_financial"].copy()
            else:
                if has_digital:
                    strategy["circle_back_phone"] = True
            strategy["priority"] = "get_phone_number"

        # Phase 4: Extract financial (turns 8-10)
        elif turn_number <= 10:
            strategy = self.PHASE_STRATEGIES["extract_financial"].copy()
            if has_account:
                strategy = self.PHASE_STRATEGIES["stall"].copy()
            strategy["priority"] = "get_bank_account"

        # Phase 5: Stall (turns 11+)
        else:
            strategy = self.PHASE_STRATEGIES["stall"].copy()
            strategy["priority"] = "waste_time"

        # ── MISSING INTEL OVERRIDE ────────────────────────────────────────────
        # After choosing baseline strategy, inject specific missing categories
        # so the LLM always targets what hasn't been extracted yet.
        missing = []
        if not has_phone:   missing.append("phone_number")
        if not has_upi:     missing.append("upi_id")
        if not has_account: missing.append("bank_account")
        if not has_email:   missing.append("email_address")
        if not has_url:     missing.append("phishing_link")
        if not has_case_id: missing.append("case_id / reference_number")
        if missing:
            strategy["missing_intel"] = missing
            strategy["extraction_targets"] = missing[:2]  # prioritise top 2 gaps

        # Special case: if scammer is asking for OTP/PIN/CVV, redirect to extraction
        if any(req in scammer_requesting for req in ["otp", "cvv", "pin", "password"]):
            strategy["redirect_otp"] = True
            strategy["redirect_message"] = "Turn OTP request into extraction opportunity"

        # Special case: if scammer is REFUSING to share info, pivot extraction target
        if conversation_history:
            last_scammer_msg = ""
            for msg in reversed(conversation_history):
                if msg.get("sender") == "scammer":
                    last_scammer_msg = msg.get("text", "").lower()
                    break
            if self._detect_refusal(last_scammer_msg):
                strategy["scammer_refused"] = True
                strategy["refusal_msg"] = last_scammer_msg

        logger.info(f"[Director] Turn {turn_number}: Strategy='{strategy['name']}', "
                   f"Priority='{strategy.get('priority', 'N/A')}', "
                   f"Targets={strategy.get('extraction_targets', [])}")

        return strategy

    def assess_conversation_quality(
        self,
        conversation_history: List[Dict],
        intelligence_extracted: Dict
    ) -> float:
        """
        Assess how well the conversation is going (0-1 score).
        
        Factors:
        - Is scammer still responding? (length of history)
        - Are we extracting intelligence? (items found)
        - Is scammer getting suspicious? (keywords in messages)
        
        Returns:
            Quality score 0.0 (bad) to 1.0 (excellent)
        """
        if not conversation_history:
            return 0.5  # Neutral for first turn

        score = 0.5  # Start neutral

        # Positive: scammer is still engaged (long conversation)
        scammer_messages = [m for m in conversation_history if m.get("sender") == "scammer"]
        if len(scammer_messages) > 3:
            score += 0.1
        if len(scammer_messages) > 6:
            score += 0.1

        # Positive: we've extracted intelligence
        total_intel = sum(len(v) for v in intelligence_extracted.values() if isinstance(v, list))
        if total_intel > 0:
            score += min(total_intel * 0.1, 0.3)

        # Negative: scammer showing suspicion
        if scammer_messages:
            last_msg = scammer_messages[-1].get("text", "").lower()
            suspicion_words = ["scam", "fraud", "fake", "bot", "ai", "robot", "automated", "suspicious"]
            if any(word in last_msg for word in suspicion_words):
                score -= 0.3

        # Negative: very short scammer messages (disengaging)
        if scammer_messages:
            avg_length = sum(len(m.get("text", "")) for m in scammer_messages) / len(scammer_messages)
            if avg_length < 20:
                score -= 0.1

        return max(0.0, min(1.0, score))

    def _detect_refusal(self, text: str) -> bool:
        """Detect if the scammer is refusing to share information."""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in self.REFUSAL_PATTERNS)

    def _get_refusal_pivot_hint(self, conversation_history: list) -> str:
        """
        When scammer refuses to share info, return a pivot hint for the persona.
        Looks at recent conversation to determine what was refused and what to pivot to.
        """
        # Find what the agent most recently asked for (from last agent message)
        last_asked = "phone"  # default pivot start
        for msg in reversed(conversation_history or []):
            if msg.get("sender") == "agent":
                text = msg.get("text", "").lower()
                if any(w in text for w in ["phone", "number", "contact", "whatsapp", "call"]):
                    last_asked = "phone"
                elif any(w in text for w in ["email", "mail"]):
                    last_asked = "email"
                elif any(w in text for w in ["upi", "link", "website", "url"]):
                    last_asked = "upi_or_link"
                elif any(w in text for w in ["employee", "id", "company", "branch"]):
                    last_asked = "company_id"
                break

        # Find the pivot hint
        for pivot in self.REFUSAL_PIVOT_SEQUENCE:
            if pivot["refused"] == last_asked:
                return pivot["pivot_hint"]
        return "Scammer refusing. Pivot to a different extraction target (email, UPI ID, or company name)."

    def decide(
        self,
        scam_type: str,
        turn_number: int,
        current_persona: Optional[str],
        intelligence_log: Dict[str, Any],
        conversation_history: Optional[List[Dict]] = None,
        accumulated_intelligence: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Main decision function — called before each persona response.
        
        Args:
            scam_type: Detected scam type
            turn_number: Current turn number
            current_persona: Currently active persona
            intelligence_log: Latest INTELLIGENCE_LOG from analyst
            conversation_history: Full conversation history
            accumulated_intelligence: All intelligence gathered so far
            
        Returns:
            Director decision dict with persona, strategy, and guidance
        """
        # Assess conversation quality
        quality = self.assess_conversation_quality(
            conversation_history or [],
            accumulated_intelligence or {}
        )

        # Select persona
        persona, should_switch = self.select_persona(
            scam_type=scam_type,
            current_persona=current_persona,
            turn_number=turn_number,
            conversation_quality=quality
        )

        # Select strategy
        strategy = self.select_strategy(
            turn_number=turn_number,
            extracted_so_far=accumulated_intelligence or {},
            scammer_requesting=intelligence_log.get("scammer_requesting", []),
            scam_type=scam_type,
            conversation_history=conversation_history
        )

        # Build additional context for persona agent
        additional_context = self._build_context_hint(strategy, intelligence_log, turn_number, conversation_history)

        decision = {
            "persona": persona,
            "should_switch_persona": should_switch,
            "strategy": strategy,
            "conversation_quality": quality,
            "additional_context": additional_context,
            "turn_number": turn_number,
            "scam_type": scam_type,
        }

        logger.info(f"[Director] Decision: persona={persona}, switch={should_switch}, "
                   f"quality={quality:.2f}, strategy={strategy['name']}")

        return decision

    def _build_context_hint(
        self,
        strategy: Dict,
        intelligence_log: Dict,
        turn_number: int,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """Build additional context hint for the persona agent."""
        hints = []

        # Strategy hint
        hints.append(f"DIRECTOR STRATEGY: {strategy['name']} — {strategy['description']}")

        # Extraction targets
        targets = strategy.get("extraction_targets", [])
        if targets:
            hints.append(f"EXTRACTION TARGETS THIS TURN: {', '.join(targets)}")

        # ── MISSING INTEL BLOCK ───────────────────────────────────────────────
        # Tell the persona agent exactly what data is still missing so it
        # knows what to ask for this turn without wasting the question.
        missing = strategy.get("missing_intel", [])
        if missing:
            hints.append(
                f"\n🚨 MISSING INTEL — YOU MUST ASK FOR ONE OF THESE THIS TURN:\n"
                + "\n".join(f"  ❌ {item}" for item in missing)
                + "\n✅ If scammer shared it, acknowledge and IMMEDIATELY ask for the next missing item."
            )
        if turn_number >= 7 and missing:
            # Escalation: approaching end of conversation
            hints.append(
                f"⚠️ ONLY {10 - turn_number} TURNS LEFT! You MUST collect the above intel NOW."
                " Ask directly — don't delay."
            )

        # OTP redirect
        if strategy.get("redirect_otp"):
            hints.append("⚠️ SCAMMER ASKING FOR OTP/PIN — DO NOT PROVIDE. Instead ask for their contact details.")

        # ── REFUSAL HANDLING ─────────────────────────────────────────────────────
        if strategy.get("scammer_refused"):
            pivot_hint = self._get_refusal_pivot_hint(conversation_history or [])
            hints.append(
                f"\n🔄 SCAMMER REFUSED TO SHARE INFO. DO NOT repeat the same question.\n"
                f"PIVOT TACTIC: {pivot_hint}\n"
                "EXAMPLE RESPONSES BY PERSONA:\n"
                "  Uncle:   'Achha beta, thik hai. Then at least tell me your office address? Or email?'\n"
                "  Worried: 'Oh okay...then how do I verify this is real? Your email?'\n"
                "  Aunty:   'Acha beta, no problem. Then bata do company ka naam?'\n"
                "  Student: 'Ok bro, np. Send ur company website link then?'\n"
                "  TechSavvy: 'Okay. Then send me official email from @company domain.'\n"
                "Keep the conversation going. Do not sound upset. Pivot naturally."
            )

        # ── CIRCLE BACK TO PHONE ──────────────────────────────────────────────────
        if strategy.get("circle_back_phone"):
            hints.append(
                "\n📞 CIRCLE BACK TO PHONE: You have their email/UPI/link. Now ASK FOR PHONE naturally.\n"
                "Frame it as needing easier/faster contact — NOT as interrogation.\n"
                "EXAMPLE RESPONSES BY PERSONA:\n"
                "  Uncle:   'Achha, one more thing beta — phone number bhi dedo? SMS se contact easy hoga.'\n"
                "  Worried: 'Okay...and what is your direct number? Email takes time, phone is faster.'\n"
                "  Aunty:   'Beta link mila, thank you! Ek WhatsApp number bhi dena? More clear hoga.'\n"
                "  Student: 'Got the link! Also send ur number? Easier to clarify stuff quickly 😊'\n"
                "  TechSavvy: 'Received. For faster verification, your direct number?'\n"
                "Ask casually — you already have something from them, this is just a natural follow-up."
            )

        # Tactics detected
        tactics = intelligence_log.get("tactics_detected", [])
        if "urgency" in tactics:
            hints.append("Scammer using URGENCY tactic — show mild panic but ask for verification first.")
        if "threat" in tactics:
            hints.append("Scammer using THREAT tactic — show fear but ask for official credentials.")
        if "authority" in tactics:
            hints.append("Scammer claiming AUTHORITY — ask for badge/employee ID to verify.")

        return "\n".join(hints)


# Global instance
conversation_director = ConversationDirectorAgent()
