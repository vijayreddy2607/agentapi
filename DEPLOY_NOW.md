# 🚀 QUICK PRODUCTION DEPLOYMENT GUIDE

**Time Remaining**: 15 minutes until 2 PM deadline ⏰

---

## Option 1: Render Deployment (RECOMMENDED - Simplest)

If you're using Render (most common):

### Step 1: Open Render Dashboard
1. Go to https://dashboard.render.com
2. Log in to your account
3. Find your honeypot API service

### Step 2: Trigger Manual Deploy
1. Click on your service name
2. Click **"Manual Deploy"** button (top right)
3. Select **"Deploy latest commit"**
4. Click **"Deploy"**

### Step 3: Wait for Deployment
- Deployment usually takes **2-5 minutes**
- Watch for "Live" status
- Green checkmark = Successful ✅

### Step 4: Verify Deployment
```bash
# Test your deployed URL
curl https://your-app.onrender.com/

# Should return 200 or 401 (not 404 or 500)
```

---

## Option 2: If Using Other Platforms

### Heroku
```bash
# In your project directory
git push heroku main

# Or force push if needed
git push heroku main --force
```

### Railway
```bash
# Railway auto-deploys from GitHub
# Just verify it's connected to your repo
# Go to https://railway.app/dashboard
# Check deployment logs
```

### Vercel/Netlify
```bash
# These auto-deploy from GitHub
# Check dashboard for latest deployment
# Should auto-deploy after your git push
```

### Self-Hosted Server (VPS/EC2)
```bash
# SSH into your server
ssh user@your-server-ip

# Navigate to project
cd /path/to/honeypot

# Pull latest code
git pull origin main

# Restart service
pm2 restart honeypot
# OR
sudo systemctl restart honeypot
```

---

## Option 3: Don't Know Your Platform?

### Find Your Deployment URL
Check your GUVI submission to see what URL you submitted:
- `https://your-app.onrender.com` → **Render**
- `https://your-app.herokuapp.com` → **Heroku**
- `https://your-app.railway.app` → **Railway**
- `https://your-app.vercel.app` → **Vercel**
- Custom domain → Check DNS records or contact host

---

## Quick Verification After Deploy

### Test 1: Basic Connectivity
```bash
curl https://YOUR-DEPLOYED-URL/
```
Expected: Any response (not timeout)

### Test 2: Email Extraction
```bash
curl -X POST https://YOUR-DEPLOYED-URL/ \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "production-test",
    "message": {
      "sender": "scammer",
      "text": "Email fraud@test.com immediately!",
      "timestamp": "2025-02-16T14:00:00Z"
    },
    "conversationHistory": [],
    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
  }'
```

Expected: JSON response with "status" and "reply" fields

---

## If Deployment is Taking Too Long

### Quick Fix: Use Current Deployment
Your current deployment **might already work** if it auto-deployed from GitHub!

Many platforms auto-deploy when you push to main branch.

**Check**:
1. Go to your deployment dashboard
2. Look for latest deployment time
3. If it shows your recent commit (b717f23), **you're good!**

---

## Re-submit on GUVI

Once deployed:

1. Go to GUVI hackathon platform
2. Find "Final Submission: API Endpoints"
3. Click **"Edit Submission"** or **"Submit"**
4. Enter:
   - **Deployment URL**: Your production URL
   - **API Key**: (leave blank if not using)
   - **GitHub URL**: `https://github.com/vijayreddy2607/agent-api`
5. Click **"Submit"**

---

## Troubleshooting

### Deployment Fails
- Check build logs in platform dashboard
- Common issue: Missing `.env` file
- Solution: Add environment variables in platform dashboard

### Still Getting Old Score
- Clear GUVI cache (if possible)
- Wait 2-3 minutes for platform cache to clear
- Test your endpoint directly to verify it's working

### Out of Time
- Submit current deployment anyway
- GUVI will re-evaluate
- Email support if needed

---

## What to Submit

```
Deployment URL: https://your-app.[platform].com
API Key: (leave blank)
GitHub URL: https://github.com/vijayreddy2607/agent-api
```

**Don't forget**: GitHub URL must be **public** (already done ✅)

---

## Time Checklist

- [ ] Deploy to production (2-5 mins)
- [ ] Verify deployment works (1 min)
- [ ] Re-submit on GUVI (2 mins)
- [ ] Relax! ✅

**You've got this!** 🚀
