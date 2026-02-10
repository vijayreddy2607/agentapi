"""Data models for intelligence tracking."""
from pydantic import BaseModel, Field
from typing import Literal


class Intelligence(BaseModel):
    """Accumulated intelligence from conversations."""
    bankAccounts: set[str] = Field(default_factory=set)
    upilds: set[str] = Field(default_factory=set)
    phishingLinks: set[str] = Field(default_factory=set)
    phoneNumbers: set[str] = Field(default_factory=set)
    suspiciousKeywords: set[str] = Field(default_factory=set)
    
    def add_bank_account(self, account: str):
        """Add a bank account to intelligence."""
        self.bankAccounts.add(account)
    
    def add_upi_id(self, upi_id: str):
        """Add a UPI ID to intelligence."""
        self.upilds.add(upi_id)

    
    def add_phishing_link(self, link: str):
        """Add a phishing link to intelligence."""
        self.phishingLinks.add(link)
    
    def add_phone_number(self, phone: str):
        """Add a phone number to intelligence."""
        self.phoneNumbers.add(phone)
    
    def add_keyword(self, keyword: str):
        """Add a suspicious keyword to intelligence."""
        self.suspiciousKeywords.add(keyword)
    
    def to_dict(self) -> dict:
        """Convert to dictionary with lists instead of sets."""
        return {
            "bankAccounts": list(self.bankAccounts),
            "upilds": list(self.upilds),
            "phishingLinks": list(self.phishingLinks),
            "phoneNumbers": list(self.phoneNumbers),
            "suspiciousKeywords": list(self.suspiciousKeywords)
        }
    
    def count_items(self) -> int:
        """Count total intelligence items."""
        return (
            len(self.bankAccounts) +
            len(self.upilds) +
            len(self.phishingLinks) +
            len(self.phoneNumbers) +
            len(self.suspiciousKeywords)
        )


class ScamDetection(BaseModel):
    """Result of scam detection."""
    is_scam: bool
    confidence: float  # 0.0 to 1.0
    scam_type: Literal[
        # Enhanced classifier types (12 specific types)
        "bank_kyc",              # Bank KYC/verification scams
        "upi_scam",              # UPI/payment app scams
        "credit_card",           # Credit card fraud
        "investment",            # Investment/trading scams
        "police_legal",          # Police/legal threats
        "tax_refund",            # Tax/Aadhaar scams
        "govt_scheme",           # Government scheme scams
        "job_offer",             # Job/work-from-home scams
        "prize_lottery",         # Prize/lottery scams
        "bill_payment",          # Bill payment scams
        "romance",               # Romance/friendship scams
        "delivery",              # Package delivery scams
        # Legacy types (for backward compatibility)
        "bank_fraud",
        "upi_fraud",
        "phishing",
        "legal_threat",
        "authority_impersonation",
        "unknown"
    ]
    recommended_agent: Literal["uncle", "worried", "techsavvy", "aunty", "student"]
    reasoning: str = ""
