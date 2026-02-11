"""Regex patterns for intelligence extraction."""
import re

# UPI ID Pattern: word@word (e.g., scammer@paytm, user@ybl)
UPI_PATTERN = re.compile(r'([a-zA-Z0-9._-]+@[a-zA-Z0-9]+)', re.IGNORECASE)

# Bank Account Pattern: 11-18 digits ONLY (exclude 10-digit phone numbers!)
# Matches: 1234567890123456, 12345678901, 1234-5678-9012-3456
BANK_ACCOUNT_PATTERN = re.compile(r'\b(\d{11,18}|\d{4}[-\s]?\d{4}[-\s]?\d{4,10})\b')

# Phone Number Pattern: Indian phone numbers (various formats)
PHONE_PATTERN = re.compile(r'(\+?91[-\s]?[6-9]\d{9}|\b[6-9]\d{9}\b)')

# URL Pattern: http/https links
URL_PATTERN = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)

# 🆕 EMPLOYEE ID PATTERN: Extracts employee/customer IDs
# Matches: ID 12345, employee ID: 98765, EMP12345, employee ID is 4521
EMPLOYEE_ID_PATTERN = re.compile(
    r'(?:employee\s*id|emp\s*id|staff\s*id|customer\s*id|id)[\s:]*(?:is\s+)?([A-Z0-9]{4,10})',
    re.IGNORECASE
)

# 🆕 NAME PATTERN: Extracts names (including titles like Mr./Mrs./Ms.)
# Matches: "Mera naam Mr. Rajesh Kumar hai", "Name is Rohit Kumar", "my name Amit"
NAME_PATTERN = re.compile(
    r'(?:name|naam)(?:\s+is|\s+hai)?[\s:]+(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
    re.IGNORECASE
)

# 🆕 ADDRESS PATTERN: Extracts addresses (handles floor numbers!)
# Matches: "123, MG Road", "5th floor, ABC Building", "XYZ Road, Andheri"
ADDRESS_PATTERN = re.compile(
    r'(\d+(?:st|nd|rd|th)?\s+(?:floor|Floor)[,\s]+[A-Za-z\s]+(?:Building|Tower|Complex|Mall)[,\s]+[A-Za-z\s]+|'  # 5th floor, ABC Building
    r'\d+[/-]?\d*,?\s+[A-Za-z\s]+(?:Road|St|Street|Avenue|Floor|Tower|Building|Complex|Mall)[,\s]+[A-Za-z\s]+|'  # 123, MG Road
    r'[A-Z][A-Za-z]+\s+(?:Road|Street|Avenue)[,\s]+[A-Z][A-Za-z\s,]+)',  # XYZ Road, Andheri
    re.IGNORECASE
)

# 🆕 OFFICE/BRANCH PATTERN: Extracts office/branch mentions
OFFICE_PATTERN = re.compile(
    r'((?:Main|Head|Branch|Andheri|Bandra|Mumbai)\s+(?:Office|Branch|West|East)[,\s]*[A-Za-z0-9\s,/-]*)',
    re.IGNORECASE
)

# Suspicious Keywords
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

# Payment App Names
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
    """Extract bank account numbers from text (exclude phone numbers!)."""
    matches = BANK_ACCOUNT_PATTERN.findall(text)
    # Filter out phone numbers:
    # - Must be at least 11 digits (not 10-digit phone)
    # - If exactly 10 digits, must NOT start with 6-9 (Indian phone pattern)
    filtered = []
    for m in matches:
        clean = re.sub(r'[-\s]', '', m)
        if len(clean) >= 11:
            filtered.append(m)
        elif len(clean) == 10 and not clean[0] in '6789':
            # 10-digit number that doesn't look like phone
            filtered.append(m)
    return filtered


def extract_phone_numbers(text: str) -> list[str]:
    """Extract phonenumbers from text."""
    matches = PHONE_PATTERN.findall(text)
    # Clean up format: remove +91, spaces, dashes
    cleaned = []
    for match in matches:
        clean = re.sub(r'[\s-]', '', match)
        if clean.startswith('+91'):
            clean = clean[3:]
        elif clean.startswith('91') and len(clean) == 12:
            clean = clean[2:]
        cleaned.append('+91-' + clean)
    return list(set(cleaned))  # Remove duplicates


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    return URL_PATTERN.findall(text)


def extract_employee_ids(text: str) -> list[str]:
    """🆕 Extract employee/customer IDs."""
    return EMPLOYEE_ID_PATTERN.findall(text)


def extract_names(text: str) -> list[str]:
    """🆕 Extract names from text."""
    return NAME_PATTERN.findall(text)


def extract_addresses(text: str) -> list[str]:
    """🆕 Extract addresses from text."""
    addresses = ADDRESS_PATTERN.findall(text)
    offices = OFFICE_PATTERN.findall(text)
    return list(set(addresses + offices))


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
