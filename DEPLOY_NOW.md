# 🚀 URGENT: Deploy Latest Optimizations to Render

## Problem
Your Render deployment is **timing out** because it's running **old code**. The latest optimizations (3.5s timeout, natural responses) are **NOT deployed yet**.

## Solution: Redeploy to Render

### Step 1: Push Latest Code to GitHub (REQUIRED)

The latest commit is **NOT pushed** yet. Push it now:

```bash
cd "/Users/vijayreddy/Desktop/honey pot agent"
git push origin main
```

Enter your GitHub credentials when prompted.

### Step 2: Trigger Render Deployment

Render should auto-deploy when you push, but if it doesn't:

**Option A: Render Dashboard (Recommended)**
1. Go to https://dashboard.render.com
2. Find your `agent-api` service
3. Click "Manual Deploy" → "Deploy latest commit"
4. Wait 2-3 minutes for deployment

**Option B: Force Redeploy via Git**
```bash
# Make a dummy commit to trigger redeploy
git commit --allow-empty -m "chore: trigger render redeploy"
git push origin main
```

### Step 3: Verify Deployment

Once deployed, test the endpoint:

```bash
curl -X POST https://agent-api-dnvn.onrender.com/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "sessionId": "test-123",
    "message": {
      "sender": "scammer",
      "text": "Your account will be blocked",
      "timestamp": 1234567890
    },
    "conversationHistory": []
  }'
```

Should respond in **< 5 seconds** (not 30s timeout!)

---

## What's Being Deployed

Latest commits with optimizations:

```
0c3ac63 - fix: Remove templates completely for truly natural human responses
b74d79f - fix: Enforce much shorter responses for natural SMS-like conversation  
e9bd350 - feat: Enhance conversation quality with progressive engagement strategy
```

**Key Improvements:**
- ✅ 3.5s LLM timeout (was 6s)
- ✅ Natural human responses (no templates)
- ✅ Short messages (40-80 chars)
- ✅ Total API response < 5s

---

## Troubleshooting

### If Render Still Times Out After Deployment:

**1. Check Render Logs**
```
Dashboard → Your Service → Logs
```
Look for:
- Startup errors
- LLM API errors
- Memory issues

**2. Verify Environment Variables**
Make sure these are set in Render:
- `groq_api_key` (your Groq API key)
- `api_key` (for x-api-key auth)
- `port` = 8000

**3. Cold Start Issue**
Free tier sleeps after 15min inactivity:
- First request takes 20-30s (warms up)
- Subsequent requests < 5s
- **Solution**: Use a free uptime monitor (UptimeRobot) to ping every 14min

**4. If STILL Timing Out**
Check if Groq API is working:
```bash
export GROQ_API_KEY="your-key"
python scripts/test_short_responses.py
```

If that works locally but not on Render, it's a deployment config issue.

---

## Competition Checklist

Before Delhi AI Summit:

- [ ] Push latest code to GitHub
- [ ] Verify Render auto-deployed
- [ ] Test API response time < 5s
- [ ] Set up uptime monitor (prevent cold starts)
- [ ] Test with real scam messages
- [ ] Confirm GUVI callback works

**Your deployment URL:** 
`https://agent-api-dnvn.onrender.com`
