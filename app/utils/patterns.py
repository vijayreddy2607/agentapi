"""Regex patterns for intelligence extraction."""
import re

# UPI ID Pattern: word@word (e.g., scammer@paytm, user@ybl)
UPI_PATTERN = re.compile(r'([a-zA-Z0-9._-]+@[a-zA-Z0-9]+)', re.IGNORECASE)

# Bank Account Pattern: 11-18 digits (excludes 10-digit phone numbers)
# Changed from \d{9,18} to \d{11,18} to prevent phone number false positives
BANK_ACCOUNT_PATTERN = re.compile(r'\b(\d{4}[-\s]?\d{4}[-\s]?\d{4,10}|\d{11,18})\b')

# Phone Number Pattern: Indian phone numbers
PHONE_PATTERN = re.compile(r'\+?91[-\s]?[6-9]\d{9}|\b[6-9]\d{9}\b')

# URL Pattern: http/https links
URL_PATTERN = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
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
