# 🚀 Quick Setup Guide for Roofing Outreach AI

Your OpenAI API key is already configured! Now let's get the other services set up to complete your AI agent.

## ✅ Already Configured
- **OpenAI API** - Ready to go! ✅

## 🔧 Required Setup Steps

### 1. Twilio Setup (SMS & Voice Calls)
**What it does**: Sends SMS messages and makes voice calls to leads

**Setup Steps**:
1. Go to [https://console.twilio.com/](https://console.twilio.com/)
2. Sign up for a free account (gets you $15 credit)
3. Get your credentials:
   - **Account SID**: Found on dashboard
   - **Auth Token**: Found on dashboard (click to reveal)
   - **Phone Number**: Go to Phone Numbers → Manage → Buy a number
4. Update your `.env` file with these values

**Cost**: ~$1/month for phone number + $0.0075 per SMS

### 2. Supabase Setup (Database)
**What it does**: Stores leads, campaigns, and outreach data

**Setup Steps**:
1. Go to [https://supabase.com/](https://supabase.com/)
2. Sign up with GitHub (free tier includes 500MB database)
3. Create a new project
4. Go to Settings → API → Copy your:
   - **Project URL** (like `https://abc123.supabase.co`)
   - **Anon Key** (public key)
5. Update your `.env` file

**Cost**: Free for up to 500MB

### 3. ElevenLabs Setup (AI Voice)
**What it does**: Generates realistic voice messages for high-priority leads

**Setup Steps**:
1. Go to [https://elevenlabs.io/](https://elevenlabs.io/)
2. Sign up (free tier includes 10,000 characters/month)
3. Go to Profile → API Key
4. Copy your API key
5. Update your `.env` file

**Cost**: Free tier, then $5/month for 30k characters

### 4. LangSmith Setup (AI Monitoring) 
**What it does**: Tracks AI performance and helps optimize your agents

**Setup Steps**:
1. Go to [https://smith.langchain.com/](https://smith.langchain.com/)
2. Sign up with your email
3. Create a new organization
4. Go to Settings → API Keys → Create API Key
5. Update your `.env` file

**Cost**: Free tier includes 5k traces/month

## 🎯 Optional Setup (Recommended)

### Google Calendar Integration
**What it does**: Automatically schedules appointments with interested leads

**Setup Steps**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable Calendar API
4. Create Service Account → Download JSON credentials
5. Save as `credentials/google-credentials.json`

## 🏃‍♂️ Quick Start (Minimum Viable Setup)

If you want to test the system immediately with just lead qualification:

1. **Set up Supabase** (required for data storage)
2. **Set up LangSmith** (required for AI tracking)
3. Leave Twilio and ElevenLabs for later

The system will run and qualify leads, but outreach will be simulated.

## 📝 Update Your Business Info

Don't forget to customize these in your `.env` file:
```env
COMPANY_NAME=Your Roofing Company Name
BUSINESS_PHONE=+1234567890
SERVICE_AREA_RADIUS=50
```

## 🚀 After Setup

Once you've configured the APIs:

```bash
# Deploy the system
./deploy.sh

# Access your dashboard
# http://localhost (main dashboard)
# http://localhost:8501 (direct Streamlit)
```

## 💡 Pro Tips

1. **Start Small**: Set up Supabase and LangSmith first, add Twilio later
2. **Test Mode**: Set `DEBUG=true` in `.env` for detailed logging
3. **Free Tiers**: All services have generous free tiers to start
4. **Scaling**: Can handle 1000+ leads per day on free tiers

## 🆘 Need Help?

- **Twilio Issues**: Check phone number verification
- **Supabase Issues**: Verify project URL format
- **API Errors**: Check API key formatting (no extra spaces)
- **Docker Issues**: Run `docker-compose logs -f` for debugging

## 🎉 What Happens Next?

Once configured, your system will:
1. **Find Leads** - Scrape Facebook/Nextdoor for storm damage posts
2. **Qualify Leads** - AI scores each lead 1-100 for priority
3. **Smart Outreach** - Contact high-priority leads immediately
4. **Track Results** - Monitor success rates and optimize

Ready to launch your AI-powered roofing lead generation system! 🏠