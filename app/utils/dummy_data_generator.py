"""
Dummy Data Generator — generates realistic fake Indian personal data.

Used by the honeypot to provide believable (but fake) information to scammers
when they ask for personal details, keeping them engaged without exposing real data.
"""
import random
import string
from typing import Optional


class DummyDataGenerator:
    """Generates realistic fake Indian personal data for honeypot use."""

    # Common Indian first names
    FIRST_NAMES = [
        "Ramesh", "Suresh", "Mahesh", "Rajesh", "Dinesh",
        "Sunita", "Kavita", "Anita", "Geeta", "Priya",
        "Arjun", "Vikram", "Amit", "Rohit", "Sanjay",
        "Meena", "Rekha", "Usha", "Lata", "Asha"
    ]

    # Common Indian last names
    LAST_NAMES = [
        "Sharma", "Verma", "Gupta", "Singh", "Kumar",
        "Patel", "Shah", "Mehta", "Joshi", "Yadav",
        "Mishra", "Tiwari", "Pandey", "Dubey", "Srivastava"
    ]

    # Indian bank names for account generation
    BANKS = ["SBI", "HDFC", "ICICI", "Axis", "PNB", "BOB", "Canara", "Union"]

    # UPI handle suffixes
    UPI_HANDLES = ["@okaxis", "@okhdfcbank", "@oksbi", "@okicici", "@ybl", "@paytm", "@upi"]

    @staticmethod
    def fake_name() -> str:
        """Generate a realistic Indian name."""
        first = random.choice(DummyDataGenerator.FIRST_NAMES)
        last = random.choice(DummyDataGenerator.LAST_NAMES)
        return f"{first} {last}"

    @staticmethod
    def fake_aadhaar() -> str:
        """Generate a fake 12-digit Aadhaar number (valid format, not real)."""
        # First digit cannot be 0 or 1
        first = random.randint(2, 9)
        rest = "".join([str(random.randint(0, 9)) for _ in range(11)])
        aadhaar = f"{first}{rest}"
        # Format: XXXX XXXX XXXX
        return f"{aadhaar[:4]} {aadhaar[4:8]} {aadhaar[8:]}"

    @staticmethod
    def fake_pan() -> str:
        """Generate a fake PAN number in ABCDE1234F format."""
        letters = "".join(random.choices(string.ascii_uppercase, k=5))
        digits = "".join([str(random.randint(0, 9)) for _ in range(4)])
        last = random.choice(string.ascii_uppercase)
        return f"{letters}{digits}{last}"

    @staticmethod
    def fake_phone() -> str:
        """Generate a fake Indian mobile number."""
        # Valid Indian mobile prefixes
        prefixes = ["98", "97", "96", "95", "94", "93", "92", "91", "90",
                    "89", "88", "87", "86", "85", "84", "83", "82", "81", "80",
                    "79", "78", "77", "76", "75", "74", "73", "72", "71", "70"]
        prefix = random.choice(prefixes)
        rest = "".join([str(random.randint(0, 9)) for _ in range(8)])
        return f"+91{prefix}{rest}"

    @staticmethod
    def fake_bank_account() -> str:
        """Generate a fake bank account number (11-16 digits)."""
        length = random.randint(11, 16)
        # First digit non-zero
        first = str(random.randint(1, 9))
        rest = "".join([str(random.randint(0, 9)) for _ in range(length - 1)])
        return first + rest

    @staticmethod
    def fake_ifsc() -> str:
        """Generate a fake IFSC code."""
        bank_codes = ["SBIN", "HDFC", "ICIC", "UTIB", "PUNB", "BARB", "CNRB", "UBIN"]
        bank = random.choice(bank_codes)
        # IFSC: 4 letters + 0 + 6 alphanumeric
        suffix = "".join(random.choices(string.digits, k=6))
        return f"{bank}0{suffix}"

    @staticmethod
    def fake_upi_id(name: Optional[str] = None) -> str:
        """Generate a fake UPI ID."""
        if name:
            # Use name-based UPI
            username = name.lower().replace(" ", ".")[:10]
        else:
            username = "".join(random.choices(string.ascii_lowercase, k=6))
            username += str(random.randint(10, 99))
        handle = random.choice(DummyDataGenerator.UPI_HANDLES)
        return f"{username}{handle}"

    @staticmethod
    def fake_utr() -> str:
        """Generate a fake UTR (Unique Transaction Reference) number."""
        # UTR format: 22 alphanumeric characters
        chars = string.ascii_uppercase + string.digits
        return "".join(random.choices(chars, k=22))

    @staticmethod
    def fake_transaction_id() -> str:
        """Generate a fake transaction ID."""
        prefix = random.choice(["TXN", "PAY", "REF", "UTR"])
        digits = "".join([str(random.randint(0, 9)) for _ in range(14)])
        return f"{prefix}{digits}"

    @staticmethod
    def fake_address() -> str:
        """Generate a fake Indian address."""
        house_no = random.randint(1, 999)
        streets = [
            "Gandhi Nagar", "Nehru Colony", "Shastri Nagar", "Patel Road",
            "MG Road", "Station Road", "Civil Lines", "Rajpur Road"
        ]
        cities = [
            "Delhi", "Mumbai", "Bangalore", "Chennai", "Hyderabad",
            "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"
        ]
        street = random.choice(streets)
        city = random.choice(cities)
        pincode = random.randint(100000, 999999)
        return f"{house_no}, {street}, {city} - {pincode}"

    @staticmethod
    def fake_email(name: Optional[str] = None) -> str:
        """Generate a fake email address."""
        if name:
            username = name.lower().replace(" ", ".") + str(random.randint(10, 99))
        else:
            username = "".join(random.choices(string.ascii_lowercase, k=8))
        domains = ["gmail.com", "yahoo.com", "hotmail.com", "rediffmail.com", "outlook.com"]
        domain = random.choice(domains)
        return f"{username}@{domain}"

    @classmethod
    def get_response_for_request(cls, request_type: str) -> dict:
        """
        Get appropriate fake data based on what scammer is requesting.

        Args:
            request_type: Type of data requested (aadhaar, pan, otp, bank, upi, etc.)

        Returns:
            Dict with fake_value and log_note
        """
        request_lower = request_type.lower()

        if any(word in request_lower for word in ["aadhaar", "aadhar", "uid"]):
            val = cls.fake_aadhaar()
            return {"fake_value": val, "type": "aadhaar", "log_note": f"Provided fake Aadhaar: {val}"}

        elif any(word in request_lower for word in ["pan", "permanent account"]):
            val = cls.fake_pan()
            return {"fake_value": val, "type": "pan", "log_note": f"Provided fake PAN: {val}"}

        elif any(word in request_lower for word in ["account", "bank account", "acc no"]):
            val = cls.fake_bank_account()
            ifsc = cls.fake_ifsc()
            return {"fake_value": val, "type": "bank_account", "log_note": f"Provided fake account: {val}, IFSC: {ifsc}"}

        elif any(word in request_lower for word in ["upi", "gpay", "phonepe", "paytm"]):
            val = cls.fake_upi_id()
            return {"fake_value": val, "type": "upi_id", "log_note": f"Provided fake UPI: {val}"}

        elif any(word in request_lower for word in ["otp", "one time", "verification code"]):
            # NEVER provide OTP — return extraction tactic instead
            return {
                "fake_value": None,
                "type": "otp_blocked",
                "log_note": "OTP request blocked — redirected to extraction"
            }

        elif any(word in request_lower for word in ["transaction", "txn", "utr", "ref"]):
            val = cls.fake_transaction_id()
            return {"fake_value": val, "type": "transaction_id", "log_note": f"Provided fake TXN: {val}"}

        elif any(word in request_lower for word in ["phone", "mobile", "number", "contact"]):
            val = cls.fake_phone()
            return {"fake_value": val, "type": "phone", "log_note": f"Provided fake phone: {val}"}

        else:
            return {"fake_value": None, "type": "unknown", "log_note": "Unknown data type requested"}


# Global instance
dummy_generator = DummyDataGenerator()
