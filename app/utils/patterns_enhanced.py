"""Enhanced pattern matching for better scam detection."""
import re

# Original patterns (keep these)
UPI_PATTERN = re.compile(r'\b([a-zA-Z0-9._-]+@[a-zA-Z0-9]+)\b')
BANK_ACCOUNT_PATTERN = re.compile(r'\b(\d{4}[-\s]?\d{4}[-\s]?\d{4,10}|\d{9,18})\b')
PHONE_PATTERN = re.compile(r'\+?91[-\s]?[6-9]\d{9}|\b[6-9]\d{9}\b')
URL_PATTERN = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)

# NEW: Advanced scam patterns for higher accuracy
ADVANCED_SCAM_PATTERNS = {
    "urgency_time": re.compile(r"(within|in)\s+\d+\s+(hours?|minutes?|days?)", re.IGNORECASE),
    "money_amount": re.compile(r"(rs\.?|₹|inr)\s*\d+", re.IGNORECASE),
    "account_with_context": re.compile(r"(account|a/c)\s*(number|no\.?)?\s*:?\s*\d{9,}", re.IGNORECASE),
    "otp_request": re.compile(r"(share|send|provide|tell).{0,20}(otp|code|pin)", re.IGNORECASE),
    "phishing_click": re.compile(r"(click|tap|visit|open).{0,20}(link|url|website)", re.IGNORECASE),
    "authority_claim": re.compile(r"(i am|this is).{0,30}(manager|officer|agent|representative|executive)", re.IGNORECASE),
    "verification_demand": re.compile(r"(verify|confirm|update).{0,20}(immediately|now|urgent|today)", re.IGNORECASE),
    "threat_pattern": re.compile(r"(will be|has been)\s+(blocked|suspended|locked|deactivated|frozen)", re.IGNORECASE),
    # NEW: Lottery/Prize patterns
    "lottery_won": re.compile(r"(won|winner|congratulations|selected).{0,40}(lottery|prize|reward|cashback|gift)", re.IGNORECASE),
    "prize_claim": re.compile(r"(claim|collect|receive).{0,20}(prize|reward|money|amount|gift)", re.IGNORECASE),
}

# Original keywords
SCAM_KEYWORDS = [
    # Urgency
    "urgent", "immediately", "now", "today", "within 24 hours", "expires",
    "limited time", "hurry", "quick", "fast",
    
    # Threats
    "blocked", "suspended", "deactivated", "frozen", "locked", "banned",
    "arrest", "legal action", "court", "police", "penalty", "fine",
    
    # Verification/Authentication
    "verify", "confirm", "authenticate", "validate", "update", "secure",
    "otp", "password", "pin", "cvv", "card details",
    
    # Financial
    "account", "bank", "upi", "payment", "transfer", "refund", "prize",
    "lottery", "winner", "cashback", "reward", "bonus",
    
    # Authority Impersonation
    "rbi", "government", "tax department", "income tax", "gst",
    "custom duty", "fedex", "courier", "delivery",
    
    # Call to Action
    "click here", "call now", "reply immediately", "share", "provide",
    "send", "forward", "download", "install",
]

PAYMENT_APPS = [
    "paytm", "phonepe", "googlepay", "gpay", "bhim", "amazon pay",
    "whatsapp pay", "mobikwik", "freecharge", "airtel money"
]


def extract_upi_ids(text: str) -> list[str]:
    """Extract UPI IDs from text."""
    matches = UPI_PATTERN.findall(text.lower())
    # Filter out email addresses (basic check)
    return [m for m in matches if not any(d in m for d in ['gmail', 'yahoo', 'outlook', 'hotmail'])]


def extract_bank_accounts(text: str) -> list[str]:
    """Extract bank account numbers from text."""
    return BANK_ACCOUNT_PATTERN.findall(text)


def extract_phone_numbers(text: str) -> list[str]:
    """Extract phone numbers from text."""
    return PHONE_PATTERN.findall(text)


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    return URL_PATTERN.findall(text)


def extract_keywords(text: str) -> list[str]:
    """Extract suspicious keywords from text."""
    text_lower = text.lower()
    found_keywords = []
    
    for keyword in SCAM_KEYWORDS:
        if keyword in text_lower:
            found_keywords.append(keyword)
    
    # Also check for payment apps
    for app in PAYMENT_APPS:
        if app in text_lower:
            found_keywords.append(app)
    
    return list(set(found_keywords))  # Remove duplicates


def calculate_advanced_suspicion_score(text: str) -> float:
    """
    Calculate enhanced suspicion score using advanced patterns.
    Returns score between 0.0 and 1.0.
    
    NEW: This gives higher accuracy than basic keyword counting!
    """
    score = 0.0
    
    # Pattern-based scoring (weighted by severity)
    if ADVANCED_SCAM_PATTERNS["urgency_time"].search(text):
        score += 0.25  # "within 24 hours" type urgency
    
    if ADVANCED_SCAM_PATTERNS["money_amount"].search(text):
        score += 0.15  # Mentions specific amounts
    
    if ADVANCED_SCAM_PATTERNS["otp_request"].search(text):
        score += 0.35  # Critical: asking for OTP/PIN
    
    if ADVANCED_SCAM_PATTERNS["phishing_click"].search(text):
        score += 0.20  # Phishing attempt
    
    if ADVANCED_SCAM_PATTERNS["authority_claim"].search(text):
        score += 0.25  # Impersonation
    
    if ADVANCED_SCAM_PATTERNS["verification_demand"].search(text):
        score += 0.20  # Urgent verification
    
    if ADVANCED_SCAM_PATTERNS["threat_pattern"].search(text):
        score += 0.30  # Account threats
    
    # NEW: Lottery/Prize patterns
    if ADVANCED_SCAM_PATTERNS["lottery_won"].search(text):
        score += 0.30  # Lottery winner scam
    
    if ADVANCED_SCAM_PATTERNS["prize_claim"].search(text):
        score += 0.25  # Prize claiming scam
    
    # Basic checks
    keywords = extract_keywords(text)
    if len(keywords) >= 3:
        score += 0.20
    
    has_phone = len(extract_phone_numbers(text)) > 0
    has_upi = len(extract_upi_ids(text)) > 0
    has_url = len(extract_urls(text)) > 0
    
    if has_phone or has_upi or has_url:
        score += 0.15
    
    # Cap at 1.0
    return min(score, 1.0)


def get_scam_indicators(text: str) -> dict:
    """
    Get detailed scam indicators for analysis.
    Returns all matched patterns with explanations.
    """
    indicators = {
        "patterns_matched": [],
        "severity": "low",
        "score": 0.0,
        "explanation": []
    }
    
    score = 0.0
    
    for pattern_name, pattern_regex in ADVANCED_SCAM_PATTERNS.items():
        match = pattern_regex.search(text)
        if match:
            indicators["patterns_matched"].append({
                "type": pattern_name,
                "matched_text": match.group(0),
                "position": match.span()
            })
            
            if pattern_name == "otp_request":
                score += 0.35
                indicators["explanation"].append("🚨 HIGH RISK: Requesting OTP/PIN (classic scam tactic)")
            elif pattern_name == "threat_pattern":
                score += 0.30
                indicators["explanation"].append("⚠️  HIGH RISK: Using account threat tactics")
            elif pattern_name == "urgency_time":
                score += 0.25
                indicators["explanation"].append("⏰ MEDIUM RISK: Creating time pressure")
            elif pattern_name == "authority_claim":
                score += 0.25
                indicators["explanation"].append("👤 MEDIUM RISK: Claiming authority/official status")
            elif pattern_name == "phishing_click":
                score += 0.20
                indicators["explanation"].append("🔗 MEDIUM RISK: Requesting click on link")
            elif pattern_name == "verification_demand":
                score += 0.20
                indicators["explanation"].append("✅ MEDIUM RISK: Demanding urgent verification")
    
    # Add intelligence data
    phones = extract_phone_numbers(text)
    upis = extract_upi_ids(text)
    urls = extract_urls(text)
    
    if phones:
        indicators["explanation"].append(f"📞 Contact info: {len(phones)} phone number(s)")
    if upis:
        indicators["explanation"].append(f"💳 Payment: {len(upis)} UPI ID(s)")
    if urls:
        indicators["explanation"].append(f"🌐 Phishing: {len(urls)} URL(s)")
    
    indicators["score"] = min(score, 1.0)
    
    # Determine severity
    if indicators["score"] >= 0.7:
        indicators["severity"] = "critical"
    elif indicators["score"] >= 0.5:
        indicators["severity"] = "high"
    elif indicators["score"] >= 0.3:
        indicators["severity"] = "medium"
    else:
        indicators["severity"] = "low"
    
    return indicators
