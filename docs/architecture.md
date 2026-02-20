# Architecture — Honeypot API

## Overview

A multi-agent honeypot system that detects scam messages, engages scammers through realistic AI personas, and extracts actionable intelligence (phone numbers, UPI IDs, bank accounts, phishing links, email addresses, case IDs).

```
Incoming Message (POST /)
        │
        ▼
┌───────────────────┐
│  ScamDetector     │  Stage 1 — First message only
│  (Hybrid Pipeline)│  1. Safe pattern filter (instant)
│                   │  2. Keyword classifier (12+ scam types)
│                   │  3. LLM verification (ambiguous only)
└────────┬──────────┘
         │ scam_type + recommended_agent
         ▼
┌───────────────────┐
│ IntelligenceEx-   │  Stage 2 — Every message
│ tractorAgent      │  Regex extraction: phone, UPI, bank,
│                   │  URL, email, caseId, policyNo, orderNo
└────────┬──────────┘
         │ intel_log
         ▼
┌───────────────────┐
│ ConversationDi-   │  Stage 3 — Every message
│ rectorAgent       │  Decides: persona, strategy, context
│                   │  Tracks: shared/refused fields, suspicion
└────────┬──────────┘
         │ director_decision + additional_context
         ▼
┌───────────────────┐
│ Persona Agent     │  Stage 4 — Response generation
│ (Uncle / Aunty /  │  Turn-based strategy (1-10):
│  Student /        │  T1→phone, T2→UPI, T3→bank, T4→email
│  TechSavvy /      │  T5→link, T6-7→caseId, T8-10→stall
│  Worried)         │
└────────┬──────────┘
         │ reply text
         ▼
┌───────────────────┐
│ GUVI Callback     │  Background task — every turn
│ (finalOutput)     │  Sends: scamDetected, extractedIntel,
│                   │  engagementMetrics, agentNotes
└───────────────────┘
```

---

## Component Details

### 1. Scam Detector (`app/core/scam_detector.py`)

3-stage hybrid pipeline:
- **Stage 1** — Safe pattern filter: instantly rejects greetings, OTP confirmations, delivery notifications (no LLM cost)
- **Stage 2** — Keyword classifier: maps 50+ keywords to 12 scam categories with confidence scoring
- **Stage 3** — Groq LLM fallback: used only for ambiguous messages (bank vs govt, etc.)

Output: `scam_type` + `recommended_agent` + `confidence`

### 2. Intelligence Extractor (`app/core/intelligence_extractor.py`)

Pure regex extraction from every scammer message. Runs on both individual messages and full conversation history (re-scan at session end).

| Field | Pattern |
|---|---|
| Phone numbers | Indian formats: +91, 10-digit, hyphenated |
| UPI IDs | `name@provider` (disambiguated from emails) |
| Bank accounts | 11–18 digit numeric strings |
| URLs / Phishing links | Standard + obfuscated (hxxp://, dot com) |
| Email addresses | Standard RFC format |
| Case IDs | `case/ref/ticket/complaint ID: XXXXX` |
| Policy numbers | `policy no: XXXXX` |
| Order numbers | `order/txn/booking ID: XXXXX` |

### 3. Conversation Director (`app/agents/conversation_director_agent.py`)

Rule-based decision engine:
- Tracks what scammer has shared (`shared_fields`) or refused (`refused_fields`)
- Counts urgency signals, authority claims, suspicion triggers
- Selects next extraction target based on turn number and missing intel
- Can recommend persona switches mid-conversation

### 4. Persona Agents (`app/agents/`)

5 distinct personas, each with unique system prompts and few-shot examples:

| Persona | Target Scam Types | Character |
|---|---|---|
| Uncle | Bank fraud, KYC, UPI | Naive retired man, asks slowly |
| Aunty | Electricity, government | Trusting, needs help step by step |
| Student | Job scams, loans | Excited, asks for proof |
| TechSavvy | Crypto, tech support | Skeptical, demands WHOIS/domain checks |
| Worried | Authority impersonation | Anxious, demands official ID |

### 5. Turn Strategy (`app/core/response_generator.py`)

Aggressive 10-turn extraction schedule:
- **Turn 1**: Phone + Employee ID
- **Turn 2**: UPI ID + Bank account
- **Turn 3**: Bank account + IFSC
- **Turn 4**: Email address
- **Turn 5**: Website/phishing link
- **Turn 6–7**: Case/reference ID
- **Turn 8–10**: Stall + re-confirm missing intel

### 6. RL Agent (`app/rl/`)

Q-learning agent that selects conversation strategy based on:
- Intel extracted so far
- Turn number
- Scammer behavior signals

Actions: `ask_clarifying_question`, `request_time`, `express_confusion`, `request_callback`

### 7. GUVI Callback (`app/utils/guvi_callback.py`)

Sends a `finalOutput` payload to GUVI's evaluation endpoint after **every turn** (not just at end), so even short sessions score full intelligence extraction points.

---

## Data Flow

```
Scammer MSG → ScamDetector → IntelligenceExtractor → ConversationDirector
    → PersonaAgent (LLM) → BaseAgent (English gate + Hinglish filter)
    → Reply sent to GUVI → GUVI Callback (background task)
```

---

## Security Design

- Agent **never** shares OTP, PIN, CVV — these trigger an extraction counter-move
- API protected by `x-api-key` header authentication
- All secrets in `.env` (never committed — see `.env.example`)
- Scammer message text is never echoed back verbatim
