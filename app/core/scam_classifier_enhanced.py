"""Enhanced scam classifier with granular categorization."""
from typing import Dict, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class EnhancedScamClassifier:
    """Classify scams into specific categories for better persona matching."""
    
    # Scam type patterns with keywords
    SCAM_PATTERNS = {
        "bank_kyc": {
            "keywords": ["kyc", "account blocked", "verify account", "update kyc",
                        "hdfc", "sbi", "icici", "axis", "bank", "reactivate",
                        "suspended account", "verify bank", "unrecognized device", 
                        "verification hold", "refundable security", "netbanking fraud prevention",
                        "yono", "re-kyc", "rbi circular"],
            "weight": 1.0
        },
        
        "upi_scam": {
            "keywords": ["paytm", "google pay", "phonepe", "gpay", "upi",
                        "upi id", "payment failed", "wallet", "bhim",
                        "payment app", "transaction failed", "salary-error", 
                        "erroneous salary", "automatic bank reversal", "npci compliance",
                        "device verification hold", "scan merchant qr", "merchant qr", 
                        "refund service", "amazon pay", "link expires"],
            "weight": 1.0
        },
        
        "credit_card": {
            "keywords": ["cvv", "card number", "credit card", "debit card",
                        "pin", "otp", "card details", "card blocked",
                        "card verification", "suspicious activity", "fraud transaction",
                        "card ending", "fraud department", "card security",
                        "block transaction", "verify card"],
            "weight": 1.0
        },
        
        "investment": {
            "keywords": ["bitcoin", "crypto", "trading", "profit", "investment",
                         "returns", "forex", "stock tip", "guaranteed",
                         "earn money", "double money", "mlm"],
            "weight": 1.0
        },
        
        "police_legal": {
            "keywords": ["police", "cyber cell", "arrest", "legal action",
                        "court", "fir", "complaint", "case", "warrant",
                        "cybercrime", "crime", "cbi", "enforcement directorate", 
                        "digital arrest", "digital surveillance", "virtual investigation", 
                        "money laundering", "pmla", "provisional attachment", "virtual appearance",
                        "scheduled substance", "parcel intercepted", "faceless assessment", 
                        "high-risk mismatch", "income tax department"],
            "weight": 1.0
        },
        
        "tax_refund": {
            "keywords": ["tax refund", "income tax", "gst", "aadhaar",
                        "pan card", "refund amount", "tax department",
                        "aadhaar update", "pan update", "faceless assessment"],
            "weight": 1.0
        },
        
        "govt_scheme": {
            "keywords": ["pm kisan", "subsidy", "lpg", "ration",
                        "voter id", "election", "government",
                        "pm scheme", "government benefit"],
            "weight": 1.0
        },
        
        "job_offer": {
            "keywords": ["work from home", "job offer", "earn", "salary",
                        "hiring", "amazon job", "data entry", "part time",
                        "vacancy", "apply now", "job opening", 
                        "background verification deposit", "refundable deposit", 
                        "adjustable in first salary", "tcs digital", "campus recruitment"],
            "weight": 1.0
        },
        
        "prize_lottery": {
            "keywords": ["won", "winner", "prize", "lottery", "congratulations",
                        "lucky", "gift card", "iphone", "selected",
                        "free gift", "reward", "amazon pay refund"],
            "weight": 1.0
        },
        
        "bill_payment": {
            "keywords": ["bill pending", "electricity", "gas bill", "broadband",
                        "overdue", "disconnection", "payment due",
                        "service suspended", "bill payment"],
            "weight": 1.0
        },
        
        "romance": {
            "keywords": ["lonely", "friendship", "beautiful", "handsome",
                        "love", "dear", "hello beautiful", "friend",
                        "relationship"],
            "weight": 1.0
        },
        
        "delivery": {
            "keywords": ["package", "courier", "delivery", "customs",
                        "cod", "shipment", "fedex", "dhl", "parcel",
                        "order delivery", "airway bill"],
            "weight": 1.0
        }
    }
    
    # Persona mapping for each scam type
    PERSONA_MAPPING = {
        "bank_kyc": "uncle",          # Uncle best for bank scams
        "upi_scam": "uncle",          # Uncle confused about apps
        "credit_card": "worried",      # Worried about card fraud
        "investment": "techsavvy",     # Tech-savvy challenges investment
        "police_legal": "worried",     # Worried panics at legal threats
        "tax_refund": "worried",       # Worried about tax issues
        "govt_scheme": "uncle",        # Uncle interested in schemes
        "job_offer": "student",        # Student excited about jobs ✨ NEW
        "prize_lottery": "aunty",      # Aunty loves prizes ✨ NEW
        "bill_payment": "worried",     # Worried about bills
        "romance": "aunty",            # Aunty lonely/social ✨ NEW
        "delivery": "worried",         # Worried about package
        "unknown": "uncle"             # Default to Uncle
    }
    
    @staticmethod
    def normalize_typos(text: str) -> str:
        """
        Normalize common typo/obfuscation patterns used by scammers.
        
        Examples:
            - 'bl0cked' → 'blocked'
            - 'acct' → 'account'
            - 'verif y' → 'verify'
            - 'ur gent' → 'urgent'
        """
        normalized = text.lower()
        
        # Leet speak and number substitutions
        substitutions = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a',
            '5': 's', '7': 't', '8': 'b', '@': 'a'
        }
        for char, replacement in substitutions.items():
            normalized = normalized.replace(char, replacement)
        
        # Remove extra spaces (catches "verif y" → "verify")
        normalized = re.sub(r'\s+', '', normalized)
        
        # Common abbreviations
        abbreviations = {
            'acct': 'account',
            'acc': 'account',
            'blk': 'block',
            'blkd': 'blocked',
            'verif': 'verify',
            'verf': 'verify',
            'urgnt': 'urgent',
            'immed': 'immediate',
            'pls': 'please',
            'msg': 'message',
            'yr': 'your',
            'ur': 'your',
            'phn': 'phone',
            'ph': 'phone'
        }
        
        for abbr, full in abbreviations.items():
            normalized = re.sub(r'\b' + abbr + r'\b', full, normalized)
        
        return normalized
    
    def classify(self, message: str) -> Tuple[str, str, float]:
        """
        Classify scam message into specific type.
        
        Args:
            message: Scam message text
            
        Returns:
            Tuple of (scam_type, recommended_persona, confidence)
        """
        message_lower = message.lower()
        # Also normalize for typo tolerance
        message_normalized = self.normalize_typos(message)
        
        # Score each scam type
        scores = {}
        for scam_type, pattern in self.SCAM_PATTERNS.items():
            score = 0
            keywords_found = []
            
            for keyword in pattern["keywords"]:
                # Check both original and normalized versions
                if keyword in message_lower or keyword in message_normalized:
                    score += pattern["weight"]
                    keywords_found.append(keyword)
            
            if score > 0:
                scores[scam_type] = {
                    "score": score,
                    "keywords": keywords_found
                }
        
        # Get best match
        if scores:
            best_type = max(scores.items(), key=lambda x: x[1]["score"])
            scam_type = best_type[0]
            confidence = min(best_type[1]["score"] / 3.0, 1.0)  # Normalize to 0-1
            
            logger.info(
                f"🎯 Classified as '{scam_type}' "
                f"(confidence: {confidence:.2f}, "
                f"keywords: {best_type[1]['keywords']})"
            )
        else:
            scam_type = "unknown"
            confidence = 0.5
            logger.debug("Could not classify scam type via keywords, defaulting to 'unknown'")

        
        # Get recommended persona
        persona = self.PERSONA_MAPPING.get(scam_type, "uncle")
        
        logger.info(f"👤 Recommended persona: {persona}")
        
        return scam_type, persona, confidence
    
    def get_scam_description(self, scam_type: str) -> str:
        """Get human-readable description of scam type."""
        descriptions = {
            "bank_kyc": "Bank account verification/KYC update scam",
            "upi_scam": "UPI/Payment app scam",
            "credit_card": "Credit/debit card fraud",
            "investment": "Investment/trading scam",
            "police_legal": "Police/legal threat scam",
            "tax_refund": "Tax refund/government document scam",
            "govt_scheme": "Government scheme scam",
            "job_offer": "Job offer/work-from-home scam",
            "prize_lottery": "Prize/lottery winner scam",
            "bill_payment": "Bill payment/service suspension scam",
            "romance": "Romance/friendship scam",
            "delivery": "Package delivery scam",
            "unknown": "Unknown scam type"
        }
        return descriptions.get(scam_type, "Unknown")


# Global classifier instance
enhanced_classifier = EnhancedScamClassifier()
