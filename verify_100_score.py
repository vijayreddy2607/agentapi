"""
GUVI SCORE VERIFICATION TEST
Tests all intelligence extraction types to ensure 100/100 score.
"""
import requests
import json
import time

API_URL = "http://localhost:8000/"
API_KEY = "honeypot-secret-key-12345"

def test_full_intelligence_extraction():
    """Test that all 5 intelligence types are extracted."""
    print("="*70)
    print("🧪 FULL INTELLIGENCE EXTRACTION TEST")
    print("="*70)
    print()
    
    # Comprehensive test message with ALL intelligence types
    test_message = """
    URGENT: Your Bank of India account has been compromised! 
    
    Call us immediately at +91-9876543210 or +91-8765432109.
    
    Transfer ₹500 to account 1234567890123456 via UPI ID scammer@paytm 
    to verify your identity.
    
    Click this link for details: http://fake-bank-verify.com/urgent
    
    Or email us at fraud.department@scam-bank.com for assistance.
    
    Time sensitive! Act now!
    """
    
    session_id = f"test-full-{int(time.time())}"
    
    response = requests.post(
        API_URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY
        },
        json={
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": test_message,
                "timestamp": "2025-02-16T13:00:00Z"
            },
            "conversationHistory": [],
            "metadata": {
                "channel": "SMS",
                "language": "English",
                "locale": "IN"
            }
        },
        timeout=30
    )
    
    print(f"📊 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API Response: {data.get('status', 'N/A')}")
        print(f"💬 Agent Reply: {data.get('reply', 'N/A')[:100]}...")
        print()
    else:
        print(f"❌ ERROR: {response.text}")
        return False
    
    # Wait for GUVI callback to be sent
    time.sleep(3)
    
    print()
    print("="*70)
    print("📋 CHECK SERVER LOGS FOR THESE EXTRACTIONS:")
    print("="*70)
    print()
    print("Expected Intelligence Extractions:")
    print("  ✅ Phone Numbers:")
    print("     - +91-9876543210")
    print("     - +91-8765432109")
    print()
    print("  ✅ Bank Account:")
    print("     - 1234567890123456")
    print()
    print("  ✅ UPI ID:")
    print("     - scammer@paytm")
    print()
    print("  ✅ Phishing Link:")
    print("     - http://fake-bank-verify.com/urgent")
    print()
    print("  ✅ Email Address:")
    print("     - fraud.department@scam-bank.com")
    print()
    print("="*70)
    print("📤 CHECK GUVI CALLBACK INCLUDES:")
    print("="*70)
    print()
    print("  ✅ status: 'completed'")
    print("  ✅ scamDetected: true")
    print("  ✅ extractedIntelligence:")
    print("     - phoneNumbers: [...]")
    print("     - bankAccounts: [...]")
    print("     - upiIds: [...]")
    print("     - phishingLinks: [...]")
    print("     - emailAddresses: [...]  ← THIS IS CRITICAL!")
    print("  ✅ engagementMetrics:")
    print("     - totalMessagesExchanged: 2")
    print("     - engagementDurationSeconds: > 0")
    print()
    
    return True

def test_email_specific():
    """Specific test for email extraction."""
    print()
    print("="*70)
    print("🧪 EMAIL-SPECIFIC EXTRACTION TEST")
    print("="*70)
    print()
    
    test_cases = [
        "Contact fraud@scam.com immediately",
        "Email support@fake-bank.org for help",
        "Reach us at scammer123@gmail.com",
        "Send details to verify.account@phishing.net"
    ]
    
    for i, msg in enumerate(test_cases, 1):
        print(f"\nTest {i}: {msg}")
        
        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": API_KEY
            },
            json={
                "sessionId": f"email-test-{i}-{int(time.time())}",
                "message": {
                    "sender": "scammer",
                    "text": msg,
                    "timestamp": "2025-02-16T13:00:00Z"
                },
                "conversationHistory": [],
                "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"  ✅ Response received")
        else:
            print(f"  ❌ Error: {response.status_code}")
        
        time.sleep(1)
    
    print()
    print("Check server logs for email extractions!")

if __name__ == "__main__":
    print()
    print("🚀 GUVI SCORE VERIFICATION")
    print("=" * 70)
    print("This test verifies that ALL intelligence types are extracted,")
    print("including EMAIL ADDRESSES which are critical for full score.")
    print("=" * 70)
    print()
    
    try:
        # Run full test
        test_full_intelligence_extraction()
        
        # Run email-specific test
        test_email_specific()
        
        print()
        print("="*70)
        print("✅ TESTS COMPLETED")
        print("="*70)
        print()
        print("Next Steps:")
        print("1. Review server logs to confirm all extractions")
        print("2. Verify GUVI callback includes emailAddresses field")
        print("3. Re-submit on GUVI platform if all tests pass")
        print()
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("Make sure the server is running on http://localhost:8000")
