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
            logger.info(f"✅ Extracted UPI ID: {upi_id}")
        
        # Extract bank accounts
        bank_accounts = patterns.extract_bank_accounts(text)
        for account in bank_accounts:
            self.intelligence.add_bank_account(account)
            logger.info(f"✅ Extracted bank account: {account}")
        
        # Extract phone numbers
        phone_numbers = patterns.extract_phone_numbers(text)
        for phone in phone_numbers:
            self.intelligence.add_phone_number(phone)
            logger.info(f"✅ Extracted phone number: {phone}")
        
        # Extract URLs
        urls = patterns.extract_urls(text)
        for url in urls:
            self.intelligence.add_phishing_link(url)
            logger.info(f"✅ Extracted URL: {url}")
        
        # 🆕 Extract Employee IDs
        employee_ids = patterns.extract_employee_ids(text)
        for emp_id in employee_ids:
            logger.info(f"✅ Extracted Employee ID: {emp_id}")
            # Don't pollute keywords with prefixes - GUVI expects clean keywords
            # self.intelligence.add_keyword(f"employee_id:{emp_id}")
        
        # 🆕 Extract Names
        names = patterns.extract_names(text)
        for name in names:
            logger.info(f"✅ Extracted Name: {name}")
            # Don't pollute keywords with prefixes - GUVI expects clean keywords
            # self.intelligence.add_keyword(f"name:{name}")
        
        # 🆕 Extract Addresses  
        addresses = patterns.extract_addresses(text)
        for address in addresses:
            logger.info(f"✅ Extracted Address: {address}")
            # Don't pollute keywords with prefixes - GUVI expects clean keywords
            # self.intelligence.add_keyword(f"address:{address}")
        
        # 🆕 Extract Landlines
        landlines = patterns.extract_landlines(text)
        for landline in landlines:
            logger.info(f"✅ Extracted Landline: {landline}")
            self.intelligence.add_phone_number(landline)  # Add as phone number
        
        # 🆕 Extract Emails
        emails = patterns.extract_emails(text)
        for email in emails:
            logger.info(f"✅ Extracted Email: {email}")
            self.intelligence.add_email_address(email)  # ← STORE IT!
        
        # 🆕 Extract Pin Codes
        pincodes = patterns.extract_pincodes(text)
        for pincode in pincodes:
            logger.info(f"✅ Extracted Pin Code: {pincode}")
            # Don't pollute keywords with prefixes - GUVI expects clean keywords
            # self.intelligence.add_keyword(f"pincode:{pincode}")
        
        # 🆕 Extract Department Heads
        dept_heads = patterns.extract_department_heads(text)
        for head in dept_heads:
            logger.info(f"✅ Extracted Department Head: {head}")
            # Don't pollute keywords with prefixes - GUVI expects clean keywords
            # self.intelligence.add_keyword(f"dept_head:{head}")
       
        # 🆕 Extract Case / Reference IDs (GUVI scoring field)
        case_ids = patterns.extract_case_ids(text)
        for cid in case_ids:
            self.intelligence.add_case_id(cid)
            logger.info(f"✅ Extracted Case ID: {cid}")

        # 🆕 Extract Policy Numbers (GUVI scoring field)
        policy_nums = patterns.extract_policy_numbers(text)
        for pol in policy_nums:
            self.intelligence.add_policy_number(pol)
            logger.info(f"✅ Extracted Policy Number: {pol}")

        # 🆕 Extract Order Numbers (GUVI scoring field)
        order_nums = patterns.extract_order_numbers(text)
        for oid in order_nums:
            self.intelligence.add_order_number(oid)
            logger.info(f"✅ Extracted Order Number: {oid}")

        # Extract suspicious keywords
        keywords = patterns.extract_keywords(text)
        for keyword in keywords:
            self.intelligence.add_keyword(keyword)
        
        # Sets are already deduplicated by nature - no need to convert
        
        return self.intelligence
    
    def extract_from_history(self, conversation_history: list) -> 'Intelligence':
        """
        Extract intelligence from ALL messages in conversation history.
        Catches data that may have been missed in earlier turns.
        """
        for msg in conversation_history:
            text = msg.get("text", "") if isinstance(msg, dict) else getattr(msg, "text", "")
            if text:
                self.extract_from_message(text)
        return self.intelligence

    def get_intelligence(self) -> Intelligence:
        """Get accumulated intelligence."""
        return self.intelligence
    
    def reset(self):
        """Reset intelligence for new session."""
        self.intelligence = Intelligence()
