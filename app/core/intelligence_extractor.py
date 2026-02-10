"""Intelligence extraction from conversations."""
from app.models.intelligence import Intelligence
from app.utils import patterns
import logging

logger = logging.getLogger(__name__)


class IntelligenceExtractor:
    """Extracts intelligence from scam conversations."""
    
    def __init__(self):
        self.intelligence = Intelligence()
    
    def extract_from_message(self, text: str) -> Intelligence:
        """
        Extract intelligence from a single message.
        
        Args:
            text: Message text to analyze
        
        Returns:
            Intelligence object with extracted data
        """
        # Extract UPI IDs
        upi_ids = patterns.extract_upi_ids(text)
        for upi_id in upi_ids:
            self.intelligence.add_upi_id(upi_id)
            logger.info(f"Extracted UPI ID: {upi_id}")
        
        # Extract bank accounts
        bank_accounts = patterns.extract_bank_accounts(text)
        for account in bank_accounts:
            self.intelligence.add_bank_account(account)
            logger.info(f"Extracted bank account: {account}")
        
        # Extract phone numbers
        phone_numbers = patterns.extract_phone_numbers(text)
        for phone in phone_numbers:
            self.intelligence.add_phone_number(phone)
            logger.info(f"Extracted phone number: {phone}")
        
        # Extract URLs
        urls = patterns.extract_urls(text)
        for url in urls:
            self.intelligence.add_phishing_link(url)
            logger.info(f"Extracted URL: {url}")
        
        # Extract suspicious keywords
        keywords = patterns.extract_keywords(text)
        for keyword in keywords:
            self.intelligence.add_keyword(keyword)
        
        return self.intelligence
    
    def get_intelligence(self) -> Intelligence:
        """Get accumulated intelligence."""
        return self.intelligence
    
    def reset(self):
        """Reset intelligence for new session."""
        self.intelligence = Intelligence()
