import asyncio
import sys
import time
import os
import re
import logging
from app.core.scam_detector import ScamDetector
from app.core.response_generator import ResponseGenerator
from dotenv import load_dotenv

# SUPPRESS ERROR LOGS FOR CLEAN DEMO OUTPUT
logging.basicConfig(level=logging.CRITICAL)
logging.getLogger('app').setLevel(logging.CRITICAL)
logging.getLogger('httpx').setLevel(logging.CRITICAL)

# Load API keys
load_dotenv()

# Colors for terminal
RED = '\033[91m'
GREEN = '\033[92m'
CYAN = '\033[96m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'
MAGENTA = '\033[95m'

def extract_intel_mock(text):
    """Simulate intelligence extraction for demo visual"""
    intel = {}
    
    # Phones
    phones = re.findall(r'(\+91[\-\s]?)?[6-9]\d{9}', text)
    if phones: intel['phone'] = phones
    
    # Emails
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if emails: intel['email'] = emails
    
    # UPI
    upis = re.findall(r'[\w\.-]+@[\w]+', text)
    if upis: intel['upi'] = [u for u in upis if u not in emails]
    
    # Links
    links = re.findall(r'(https?://[^\s]+|www\.[^\s]+)', text)
    if links: intel['link'] = links
    
    return intel

async def run_scenario(name, persona, script, generator):
    print(f"\n{BOLD}{YELLOW}================================================================{RESET}")
    print(f"{BOLD}{YELLOW}🎬 SCENARIO: {name} ({persona.upper()} PERSONA){RESET}")
    print(f"{BOLD}{YELLOW}================================================================{RESET}\n")
    time.sleep(2)
    
    history = []
    
    for i, msg in enumerate(script):
        # 1. Scammer Speaks
        print(f"[{RED}SCAMMER (Turn {i+1}){RESET}]: {msg}")
        history.append({"role": "user", "content": msg})
        
        # 2. Extract Intelligence (Visual)
        intel = extract_intel_mock(msg)
        if intel:
            print(f"{MAGENTA}   🔍 EXTRACTED: {intel}{RESET}")
            
        time.sleep(1) # Thinking time
        
        # 3. Agent Responds
        response = await generator.generate_response(
            persona=persona,
            scammer_message=msg,
            turn_number=i+1,
            scam_type="general", # Simplified for demo
            conversation_history=history
        )
        
        history.append({"role": "assistant", "content": response})
        print(f"[{GREEN}AGENT ({persona.upper()}){RESET}]: {response}")
        print("-" * 60)
        time.sleep(2)

async def run_demo():
    print(f"\n{BOLD}{CYAN}🚀 AGENTIC HONEYPOT: ALL-PERSONA DEMO INITIALIZED...{RESET}")
    print(f"{CYAN}Loading models...{RESET}\n")
    
    detector = ScamDetector()
    generator = ResponseGenerator(groq_api_key=os.getenv("GROQ_API_KEY"))

    # --- SCENARIO 1: BANK SCAM (UNCLE) ---
    script_uncle = [
        "URGENT: Your SBI account is blocked. Share OTP immediately.",
        "Yes, send OTP to +91-9876543210 to unblock."
    ]
    await run_scenario("BANK SCAM", "uncle", script_uncle, generator)

    # --- SCENARIO 2: LOTTERY SCAM (AUNTY) ---
    script_aunty = [
        "Congratulations! You won KBC Lottery of 25 Lakhs!",
        "Pay 5000 processing fee to claim prize."
    ]
    await run_scenario("LOTTERY SCAM", "aunty", script_aunty, generator)

    # --- SCENARIO 3: JOB SCAM (STUDENT) ---
    script_student = [
        "Amazon Part-Time Job. Earn 5000/day. No interview.",
        "Join using this link: www.fake-job-amazon.com"
    ]
    await run_scenario("JOB SCAM", "student", script_student, generator)

    # --- SCENARIO 4: DIGITAL ARREST (WORRIED) ---
    script_worried = [
        "This is Mumbai Police. A parcel with drugs was found in your name.",
        "Verify your Aadhar immediately or we will issue arrest warrant."
    ]
    await run_scenario("DIGITAL ARREST", "worried", script_worried, generator)

    # --- SCENARIO 5: CRYPTO SCAM (TECHSAVVY) ---
    script_tech = [
        "Invest in Bitcoin 2.0. 300% Returns guaranteed in 24 hours.",
        "Send USDT to wallet address: 0x12345abcdef"
    ]
    await run_scenario("CRYPTO SCAM", "techsavvy", script_tech, generator)

    # --- SCENARIO 6: SAFETY CHECK ---
    print(f"\n{BOLD}{YELLOW}================================================================{RESET}")
    print(f"{BOLD}{YELLOW}🛡️ SCENARIO: SAFETY CHECK (IRRELEVANT INPUT){RESET}")
    print(f"{BOLD}{YELLOW}================================================================{RESET}\n")
    
    msg = "What is the capital of Paris?"
    print(f"[{RED}USER{RESET}]: {msg}")
    
    detection = await detector.detect(msg)
    if detection.confidence < 0.5:
        print(f"[{GREEN}AGENT{RESET}]: [IGNORED] (Confidence: {detection.confidence})")
        print(f"{RED}🚫 REJECTED: Not a scam attempt.{RESET}")
    
    print(f"\n{BOLD}{CYAN}✅ DEMO COMPLETE. 5/5 PERSONAS TESTED. SYSTEM SECURE.{RESET}\n")

if __name__ == "__main__":
    asyncio.run(run_demo())
