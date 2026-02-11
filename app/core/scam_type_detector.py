"""
Scam Type Detector - Identifies scam category from message content.
Used to select appropriate persona (student, elderly, professional, etc.)
"""

import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ScamTypeDetector:
    """Detects scam type from message content to select appropriate persona."""
    
    # Keyword patterns for each scam type (case-insensitive)
    SCAM_TYPE_PATTERNS = {
        "loan": [
            "loan", "instant approval", "processing fee", "credit score",
            "disburse", "loan officer", "KYC", "eligibility", "EMI",
            "लोन", "instant.*lakh", "approved.*minutes"
        ],
        "credit_card": [
            "credit card", "CVV", "card number", "fraud transaction",
            "suspicious activity", "block.*card", "card.*expir", "card.*ending",
            "क्रेडिट कार्ड", "debit card", "ATM", "verify.*card",
            "card.*security", "fraud.*dept"  # Added more patterns
        ],
        "job": [
            "selected", "work from home", "WFH", "registration fee",
            "joining", "HR", "interview", "employ", "salary", "congratulations.*selected",
            "नौकरी", "Amazon.*job", "₹.*month", "₹.*per month"
        ],
        "investment": [
            "returns", "profit", "crypto", "trading", "invest",
            "guaranteed.*%", "fund", "stock", "forex", "bitcoin",
            "निवेश", "500%", "earn.*crore"
        ],
        "digital_arrest": [
            "CBI", "police", "arrest", "Aadhaar.*link", "illegal",
            "money.*launder", "case.*register", "court", "FIR",
            "गिरफ्तारी", "पुलिस", "jail", "fine.*lakh"
        ],
        "delivery": [
            "delivery", "package", "courier", "redeliver", "parcel",
            "Amazon.*package", "tracking", "shipment", "customs", "delivery.*failed",
            "डिलीवरी", "failed.*delivery", "pay.*₹.*redeliver"  # Added more patterns
        ],
        "phishing": [
            "KYC.*expir", "update.*account", "verify.*account",
            "link.*click", "blocked.*account", "re-.*activ",
            "केवाईसी", "expire", "suspend"
        ],
        "upi_otp": [
            "OTP", "UPI", "account.*block", "verify.*identit",
            "PIN", "transfer", "payment", "transaction",
            "ओटीपी", "यूपीआई", "urgent.*account"
        ]
    }
    
    def detect(self, text: str) -> str:
        """
        Detect scam type from message text.
        
        Args:
            text: Message content to analyze
            
        Returns:
            Scam type string (loan, credit_card, job, etc.) or "generic" if unknown
        """
        text_lower = text.lower()
        
        # Count keyword matches for each type
        scores = {}
        for scam_type, keywords in self.SCAM_TYPE_PATTERNS.items():
            score = 0
            for keyword in keywords:
                # Use regex for flexible matching
                if re.search(keyword, text_lower):
                    score += 1
            scores[scam_type] = score
        
        # Get type with highest score
        if max(scores.values()) == 0:
            logger.info("No specific scam type detected - using generic persona")
            return "generic"
        
        detected_type = max(scores, key=scores.get)
        logger.info(f"🎯 Detected scam type: {detected_type} (confidence: {scores[detected_type]} keywords)")
        
        return detected_type


# Singleton instance
scam_detector = ScamTypeDetector()
