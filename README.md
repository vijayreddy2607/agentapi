# 🍯 Honeypot API — Agentic Scam Detection System

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Llama--3.3--70b-orange)](https://groq.com)

A multi-agent honeypot system that **detects scams**, **engages scammers** through 5 distinct AI personas, and **extracts actionable intelligence** — all in real time.

---

## Description

When a scammer sends a message, this system:
1. **Detects** the scam type (bank fraud, UPI fraud, phishing, job scam, etc.)
2. **Selects** the best persona to engage (Uncle, Aunty, Student, TechSavvy, Worried)
3. **Engages** the scammer over multiple turns, extracting phone numbers, UPI IDs, bank accounts, phishing links, and email addresses
4. **Reports** all extracted intelligence to the GUVI evaluation callback

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI + Uvicorn |
| Primary LLM | Groq (llama-3.3-70b-versatile) — fast, free tier |
| LLM Orchestration | Langchain |
| Intelligence Extraction | Custom regex patterns (patterns.py) |
| RL Strategy Adaptation | Q-learning RL agent (rl_agent.py) |
| Session Persistence | SQLAlchemy (SQLite) |
| State Management | In-memory session manager + DB fallback |

---

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/vijayreddy2607/agentapi.git
cd agentapi
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

### 4. Run locally
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## API Endpoint

- **URL:** `https://agent-api-dnvn.onrender.com/honeypot`
- **Method:** POST
- **Authentication:** `x-api-key` header

**Headers:**
```
Content-Type: application/json
x-api-key: <your-api-key>
```

**Request Body:**
```json
{
  "sessionId": "unique-session-id",
  "message": {
    "sender": "scammer",
    "text": "URGENT: Your SBI account is blocked. Share OTP immediately.",
    "timestamp": "2025-01-01T00:00:00Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "reply": "Oh! Which bank is calling? What is your employee ID number?"
}
```

> Also available at: `POST /` and `POST /api/message`

---

## Architecture

### 🔍 Scam Detection Pipeline
3-stage hybrid pipeline for fast, accurate detection:
1. **Safe Pattern Filter** — instant regex check for benign greetings
2. **Keyword Classifier** — 12+ scam type categories with confidence scoring
3. **Groq LLM Verification** — used only for ambiguous messages (<1s latency)

### 🧠 Intelligence Extraction
Regex-based extraction from every message and full history re-scan at session end:
- Phone numbers (`+91-xxxxxxxxxx`, all Indian formats)
- UPI IDs (`name@provider`)
- Bank accounts (11–18 digit numeric strings)
- Phishing URLs (standard and obfuscated formats like `hxxp://`, `dot com`)
- Email addresses
- Case IDs, order numbers, policy numbers

### 🎭 5 AI Personas

| Persona | Scam Type Targets | Strategy |
|---------|-----------------|---------|
| **Uncle** | Bank fraud, KYC, UPI | Confused elderly man, asks for verification |
| **Aunty** | Electricity, Government | Trusting but needs step-by-step help |
| **Student** | Job scams, Loans | Excited, asks for company/payment details |
| **TechSavvy** | Crypto, Tech support | Skeptical, demands WHOIS/SEBI proof |
| **Worried** | Authority impersonation | Anxious, asks for official badge/ID |

### 🤖 RL Agent
Q-learning agent selects extraction strategies per turn:
- `ask_clarifying_question` — probe for identity/company
- `request_time` — stall and extract while waiting
- `express_confusion` — get scammer to repeat + clarify details
- `request_callback` — extract phone number naturally

---

## GUVI Callback Payload

At conversation end, the system sends:
```json
{
  "sessionId": "...",
  "status": "completed",
  "scamDetected": true,
  "scamType": "bank_fraud",
  "confidenceLevel": 0.95,
  "extractedIntelligence": {
    "phoneNumbers": ["+91-9876543210"],
    "upiIds": ["scammer@fakebank"],
    "bankAccounts": ["1234567890123456"],
    "phishingLinks": ["http://fake-sbi.com"],
    "emailAddresses": ["scam@fraud.com"]
  },
  "engagementMetrics": {
    "engagementDurationSeconds": 180,
    "totalMessagesExchanged": 10
  },
  "agentNotes": "RED FLAGS: OTP demand, urgency pressure, authority impersonation..."
}
```

---

## Project Structure

```
app/
├── agents/          # 5 personas + base agent + orchestrator
├── core/            # Scam detector, intelligence extractor, session manager
├── prompts/         # Per-persona system prompts
├── utils/           # Patterns, LLM client, GUVI callback, human behavior
├── models/          # Pydantic models
├── api/             # FastAPI endpoints
└── rl/              # Reinforcement learning agent
```

---

## Security

- API key authentication via `x-api-key` header
- Agent **never** shares OTP, PIN, or CVV — uses them as extraction triggers
- All keys managed via environment variables (never hardcoded)
