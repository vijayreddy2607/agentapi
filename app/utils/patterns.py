"""Regex patterns for intelligence extraction."""
import re

# UPI ID Pattern: word@bankhandle where handle has NO dot or hyphen
# e.g. scammer@paytm, user@ybl, cashback@oksbi
# NOT: offers@fake-amazon-deals.com (hyphen/dot after handle = email)
UPI_PATTERN = re.compile(r'([a-zA-Z0-9._-]+@[a-zA-Z0-9]+)(?![-.])', re.IGNORECASE)

# Bank Account Pattern: 11-18 digits ONLY (exclude 10-digit phone numbers!)
# Matches: 1234567890123456, 12345678901, 1234-5678-9012-3456
BANK_ACCOUNT_PATTERN = re.compile(r'\b(\d{11,18}|\d{4}[-\s]?\d{4}[-\s]?\d{4,10})\b')

# Phone Number Pattern: Indian phone numbers (various formats)
# Matches: 9876543210, 98765-43210, +91-9876543210, +91 98765 43210
PHONE_PATTERN = re.compile(r'(\+?91[-\s]?[6-9]\d{4}[-\s]?\d{5}|\b[6-9]\d{4}[-\s]?\d{5}\b|\+?91[-\s]?[6-9]\d{9}|\b[6-9]\d{9}\b)')

# URL Pattern: http/https links
URL_PATTERN = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)

# 🆕 OBFUSCATED URL PATTERN: Catches "dot com", "[.]com", "hxxp://", etc.
# Matches: sbi-secure dot com, example[.]com, bank-verify (dot) in, hxxp://scam
OBFUSCATED_URL_PATTERN = re.compile(
    r'(?:https?|hxxps?|h\*\*p)://[^\s]+|'  # hxxp://scam
    r'(?:[a-z0-9-]+)\s*(?:dot|\[?\.\]?|\(\s*dot\s*\))\s*(?:com|in|org|net|co|info)(?:/[^\s]*)?|'  # example dot com or (dot)
    r'(?:[a-z0-9-]+\[\.\][a-z]+(?:/[^\s]*)?)',  # example[.]com/path
    re.IGNORECASE
)


# 🆕 EMPLOYEE ID PATTERN: Extracts employee/customer IDs
# Matches: ID 12345, employee ID: 98765, EMP12345, employee ID is 4521
EMPLOYEE_ID_PATTERN = re.compile(
    r'(?:employee\s*id|emp\s*id|staff\s*id|customer\s*id|id)[\s:]*(?:is\s+)?([A-Z0-9]{4,10})',
    re.IGNORECASE
)

# 🆕 NAME PATTERN: Extracts person names
# Matches: "Rajesh Kumar", "Mera naam Rajesh Kumar hai", "I am Amit Singh"
NAME_PATTERN = re.compile(
    r'(?:naam|name|I am|main|mera naam)\s+(?:hai\s+)?([A-Z][a-z]+\s+[A-Z][a-z]+)|(?:Mr\.?|Mrs\.?|Ms\.?)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
    re.IGNORECASE
)

# 🆕 ADDRESS PATTERN: Extracts physical addresses
# Matches: 123 MG Road, 12/3 Sector 5, Plot No. 12, XYZ सिटी के मुख्य बाजार में
ADDRESS_PATTERN = re.compile(
    r'(\d+[/-]?\d*,?\s+[A-Z][A-Za-z\s]+(?:Road|Street|Sector|Plot|Floor|Building|Branch)[,\s]+[A-Za-z\s]+)',
    re.IGNORECASE
)

# 🆕 HINDI ADDRESS PATTERN: Extracts Hindi/Devanagari addresses
# Matches: XYZ सिटी के मुख्य बाजार में, दिल्ली के कनॉट प्लेस में
HINDI_ADDRESS_PATTERN = re.compile(
    r'([\u0900-\u097F\w\s]+(?:सिटी|बाजार|रोड|मार्ग|नगर|इलाका|क्षेत्र)[,\s]*[\u0900-\u097F\w\s]*)',
    re.IGNORECASE
)

# 🆕 LANDLINE PATTERN: Extracts landline numbers
# Matches: 022-12345678, 011-1234567, 0XXX-XXXXXXX
LANDLINE_PATTERN = re.compile(r'0\d{2,4}[-\s]?\d{6,8}')

# 🆕 EMAIL PATTERN: Extracts email addresses
# Matches: scammer@fake.com, support@bank.co.in
EMAIL_PATTERN = re.compile(r'[\w.-]+@[\w.-]+\.\w+')

# 🆕 PINCODE PATTERN: Extracts Indian pin codes (but NOT sequential/repeated digits)
# Matches: 110001, 400001, etc. but NOT 123456, 111111, 987654
PINCODE_PATTERN = re.compile(r'\b[1-9]\d{5}\b')

# 🆕 WRITTEN NUMBER PATTERN: Detects written-out numbers
# Matches: "nine eight seven six five", "seven zero one",  etc.
WRITTEN_NUMBER_MAP = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'
}
WRITTEN_NUMBER_PATTERN = re.compile(
    r'\b(?:zero|one|two|three|four|five|six|seven|eight|nine)(?:\s+(?:zero|one|two|three|four|five|six|seven|eight|nine)){4,}\b',
    re.IGNORECASE
)


# 🆕 DEPARTMENT HEAD PATTERN: Extracts department head/manager names
# Matches: "department head Mr. X", "head Amit Singh", "manager Raj Sharma"
DEPARTMENT_HEAD_PATTERN = re.compile(
    r'(?:department\s+head|manager|supervisor|head|boss)\s+(?:Mr\.?|Mrs\.?|Ms\.?)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
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
    """Extract UPI IDs from text.
    UPI IDs: word@bankhandle (no dots in domain part, e.g. @ybl @oksbi @fakebank)
    Emails: word@domain.tld (has dots, e.g. @gmail.com @fake-amazon-deals.com)
    """
    matches = UPI_PATTERN.findall(text.lower())
    upi_ids = []
    for m in matches:
        # UPI IDs have NO dot in the part after @
        # Emails have a dot in the domain (e.g. .com, .in)
        at_pos = m.rfind('@')
        domain_part = m[at_pos+1:] if at_pos >= 0 else ''
        if '.' not in domain_part:  # No dot = UPI ID, not email
            upi_ids.append(m)
    return list(set(upi_ids))


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


def convert_written_numbers(text: str) -> str:
    """Convert written numbers to digits. 'nine eight seven' -> '987'."""
    matches = WRITTEN_NUMBER_PATTERN.findall(text)
    for match in matches:
        words = match.lower().split()
        digits = ''.join([WRITTEN_NUMBER_MAP.get(word, '') for word in words])
        text = text.replace(match, digits)
    return text


def extract_phone_numbers(text: str) -> list[str]:
    """Extract phone numbers from text, including written ones and hyphenated formats."""
    # First convert written numbers to digits
    text_converted = convert_written_numbers(text)
    
    matches = PHONE_PATTERN.findall(text_converted)
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
    """Extract URLs from text, including obfuscated ones."""
    urls = []
    
    # Regular URLs
    urls.extend(URL_PATTERN.findall(text))
    
    # Obfuscated URLs (dot com, [.]com, etc.)
    obfuscated = OBFUSCATED_URL_PATTERN.findall(text)
    for url in obfuscated:
        # Normalize obfuscated formats
        normalized = url.replace(' dot ', '.').replace('dot ', '.').replace(' dot', '.')
        normalized = normalized.replace('[.]', '.').replace('(.)', '.')
        normalized = normalized.replace('( dot )', '.').replace('(dot)', '.')
        normalized = normalized.replace('hxxp', 'http').replace('h**p', 'http')
        if normalized not in urls:
            urls.append(normalized)
    
    return list(set(urls))  # Remove duplicates



def extract_employee_ids(text: str) -> list[str]:
    """🆕 Extract employee/customer IDs."""
    return EMPLOYEE_ID_PATTERN.findall(text)


def extract_names(text: str) -> list[str]:
    """🆕 Extract names from text."""
    matches = NAME_PATTERN.findall(text)
    # Pattern has multiple groups, findall returns tuples - flatten and filter
    names = []
    for match in matches:
        if isinstance(match, tuple):
            # Get non-empty strings from tuple
            names.extend([m for m in match if m])
        else:
            names.append(match)
    return list(set(names))  # Dedupe




def extract_addresses(text: str) -> list[str]:
    """🆕 Extract physical addresses from text (English and Hindi)."""
    addresses = []
    
    # English addresses
    addresses.extend(ADDRESS_PATTERN.findall(text))
    
    # Hindi addresses
    hindi_matches = HINDI_ADDRESS_PATTERN.findall(text)
    addresses.extend(hindi_matches)
    
    # Office patterns
    offices = OFFICE_PATTERN.findall(text)
    addresses.extend(offices)
    
    # Clean and dedupe
    cleaned = [addr.strip() for addr in addresses if len(addr.strip()) > 10]
    return list(set(cleaned))


def extract_landlines(text: str) -> list[str]:
    """Extract landline numbers."""
    matches = LANDLINE_PATTERN.findall(text)
    return list(set(matches))


def extract_emails(text: str) -> list[str]:
    """Extract email addresses (NOT UPI IDs)."""
    matches = EMAIL_PATTERN.findall(text)
    emails = []
    for m in matches:
        # Emails MUST have a dot in the domain part (e.g. .com, .in, .co.in)
        at_pos = m.rfind('@')
        domain_part = m[at_pos+1:] if at_pos >= 0 else ''
        if '.' in domain_part:  # Has dot = real email, not UPI
            emails.append(m.lower())
    return list(set(emails))


def extract_pincodes(text: str) -> list[str]:
    """Extract Indian pin codes (excluding sequential/repeated patterns)."""
    matches = PINCODE_PATTERN.findall(text)
    
    # Filter out sequential (123456, 987654) and repeated (111111) patterns
    valid_pincodes = []
    for code in matches:
        # Check if all digits are same (111111)
        if len(set(code)) == 1:
            continue
        
        # Check if sequential ascending (123456)
        if all(int(code[i]) == int(code[i-1]) + 1 for i in range(1, len(code))):
            continue
        
        # Check if sequential descending (987654)
        if all(int(code[i]) == int(code[i-1]) - 1 for i in range(1, len(code))):
            continue
        
        valid_pincodes.append(code)
    
    return list(set(valid_pincodes))


def extract_department_heads(text: str) -> list[str]:
    """Extract department head/manager names."""
    matches = DEPARTMENT_HEAD_PATTERN.findall(text)
    return list(set(matches))



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
