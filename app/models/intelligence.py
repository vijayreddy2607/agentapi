"""Data models for intelligence tracking."""
from pydantic import BaseModel, Field
from typing import Literal


class Intelligence(BaseModel):
    """Accumulated intelligence from conversations."""
    bankAccounts: set[str] = Field(default_factory=set)
    upiIds: set[str] = Field(default_factory=set)  # Fixed typo: was 'upilds'
    phishingLinks: set[str] = Field(default_factory=set)
    phoneNumbers: set[str] = Field(default_factory=set)
    suspiciousKeywords: set[str] = Field(default_factory=set)
    
    def add_bank_account(self, account: str):
        """Add a bank account to intelligence."""
        self.bankAccounts.add(account)
    
    def add_upi_id(self, upi_id: str):
        """Add a UPI ID to intelligence."""
        self.upiIds.add(upi_id)

    
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
            "upiIds": list(self.upiIds),  # Fixed typo: was 'upilds'
            "phishingLinks": list(self.phishingLinks),
            "phoneNumbers": list(self.phoneNumbers),
            "suspiciousKeywords": list(self.suspiciousKeywords)
        }
    
    def count_items(self) -> int:
        """Count total intelligence items (including keywords)."""
        return (
            len(self.bankAccounts) +
            len(self.upiIds) +
            len(self.phishingLinks) +
            len(self.phoneNumbers) +
            len(self.suspiciousKeywords)
        )
    
    def count_valuable_items(self) -> int:
        """Count ONLY valuable intelligence (excludes keywords).
        
        This is used to determine when to send GUVI callback.
        Keywords alone don't prove extraction is working.
        """
        return (
            len(self.bankAccounts) +
            len(self.upiIds) +
            len(self.phishingLinks) +
            len(self.phoneNumbers)
        )
    
    def predict_bank_names(self) -> list[str]:
        """Predict bank names based on account number length."""
        predictions = []
        for account in self.bankAccounts:
            # Remove any separators for length check
            clean_acc = account.replace("-", "").replace(" ", "")
            length = len(clean_acc)
            
            bank_name = "Unknown Bank"
            if length == 11:
                bank_name = "SBI (State Bank of India)"
            elif length == 12:
                bank_name = "ICICI Bank"
            elif length == 13:
                bank_name = "Canara Bank"
            elif length == 14:
                bank_name = "HDFC / Kotak / Bank of Baroda"
            elif length == 15:
                bank_name = "Axis / Union Bank"
            elif length == 16:
                bank_name = "Punjab National Bank (PNB)"
            
            predictions.append(f"{account} ({bank_name})")
        
        return predictions


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
        "urgency_threat",        # 🆕 Pure urgency/time-pressure scams
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
