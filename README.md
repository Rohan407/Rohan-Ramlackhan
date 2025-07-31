# 🏠 Roofing Outreach AI Agent

An AI-powered system for automated lead generation and outreach for roofing companies after storm events. This system scrapes social media platforms to find homeowners with roof damage, qualifies leads using AI, and executes multi-channel outreach campaigns.

## 🚀 Features

### 🔍 Lead Generation
- **Social Media Scraping**: Automated scraping of Facebook and Nextdoor for storm damage posts
- **Location Targeting**: Focus on specific zip codes and areas affected by storms
- **Keyword Detection**: Advanced keyword matching for roof damage indicators

### 🤖 AI-Powered Lead Qualification
- **GPT-4 Analysis**: Intelligent analysis of posts to score lead quality
- **Priority Scoring**: Automatic prioritization based on urgency and damage severity
- **Damage Type Classification**: Categorization of damage types and project value estimation

### 📞 Multi-Channel Outreach
- **SMS Campaigns**: Automated SMS outreach via Twilio
- **Voice Calls**: AI-generated voice messages using ElevenLabs
- **Calendar Integration**: Google Calendar appointment scheduling
- **Response Handling**: Intelligent processing of inbound responses

### 📊 Analytics & Monitoring
- **Real-time Dashboard**: Streamlit-powered analytics dashboard
- **Performance Tracking**: LangSmith integration for AI model monitoring
- **Campaign Analytics**: Comprehensive reporting and metrics

## 🛠️ Tech Stack

- **Backend**: Python 3.11, FastAPI, Asyncio
- **AI/ML**: OpenAI GPT-4, LangChain, LangSmith
- **Database**: Supabase (PostgreSQL)
- **Communication**: Twilio (SMS/Voice), ElevenLabs (AI Voice)
- **Scraping**: Selenium, BeautifulSoup, Playwright
- **Frontend**: Streamlit Dashboard
- **Deployment**: Docker, Docker Compose, Nginx

## 📋 Prerequisites

### Required API Keys
- **OpenAI API Key** - For AI lead qualification and message generation
- **Twilio Account** - For SMS and voice communication
- **ElevenLabs API** - For AI voice generation
- **Supabase Account** - For database and backend services
- **LangSmith API** - For AI model monitoring and evaluation
- **Google Cloud Credentials** - For calendar integration (optional)

### Optional
- **Facebook Account** - For enhanced Facebook scraping (limited access without)
- **Nextdoor Account** - For neighborhood-specific targeting

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/roofing-outreach-agent.git
cd roofing-outreach-agent
```

### 2. Set Up Environment
```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

### 3. Configure API Keys
Edit `.env` file with your credentials:
```env
OPENAI_API_KEY=sk-your-openai-api-key
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890
ELEVENLABS_API_KEY=your-elevenlabs-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
LANGSMITH_API_KEY=your-langsmith-key
COMPANY_NAME=Your Roofing Company
BUSINESS_PHONE=+1234567890
```

### 4. Deploy with Docker
```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### 5. Access Dashboard
- **Main Dashboard**: http://localhost
- **Direct Streamlit**: http://localhost:8501

## 📖 Detailed Setup

### Manual Installation (Development)

#### 1. Python Environment
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Browser Setup for Scraping
```bash
# Install playwright browsers
playwright install chromium

# For Selenium (alternative)
# Download ChromeDriver and add to PATH
```

#### 3. Google Calendar Setup (Optional)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Calendar API
4. Create service account credentials
5. Download JSON file and save as `credentials/google-credentials.json`

#### 4. Database Setup
The system uses Supabase for database management. Tables are created automatically on first run.

#### 5. Run Development Server
```bash
# Start the orchestrator
python -m workflows.main_orchestrator

# In another terminal, start the dashboard
streamlit run api/dashboard.py --server.port=8501
```

## 🎯 Usage Guide

### Creating a Campaign

#### Via Dashboard
1. Open the dashboard at http://localhost
2. Navigate to "Campaign Management"
3. Enter storm location (e.g., "Miami, FL")
4. Select urgency level and target platforms
5. Click "Launch Campaign"

#### Via Python API
```python
from workflows.main_orchestrator import run_storm_response_workflow

# Run emergency storm response
result = await run_storm_response_workflow("Miami, FL", urgency="high")
print(result)
```

### Monitoring Performance

#### Dashboard Analytics
- **Campaign Overview**: Total leads, qualification rates, conversion metrics
- **Lead Management**: Search, filter, and manage individual leads
- **Outreach Control**: Monitor SMS/call limits and success rates
- **Performance Metrics**: AI model performance and response times

#### LangSmith Integration
- Automatic tracking of AI agent performance
- Model evaluation and improvement suggestions
- Response time and accuracy monitoring

### Managing Leads

#### Lead Qualification Levels
- **Hot Leads (80-100 score)**: Immediate need, specific damage, ready to hire
- **Warm Leads (50-79 score)**: Some damage indication, might be interested
- **Cold Leads (30-49 score)**: General interest, no immediate need

#### Outreach Sequences
- **Hot Leads**: Immediate SMS + voice call + calendar scheduling
- **Warm Leads**: SMS outreach + follow-up scheduling
- **Cold Leads**: Email or SMS nurture sequence

## 🔧 Configuration

### Business Settings
```env
COMPANY_NAME=Your Roofing Company
BUSINESS_PHONE=+1234567890
SERVICE_AREA_RADIUS=50  # miles
```

### Outreach Limits
```env
MAX_DAILY_SMS=200
MAX_DAILY_CALLS=100
CALL_HOURS_START=9
CALL_HOURS_END=18
```

### AI Model Settings
The system uses GPT-4 for lead qualification with customizable prompts. Modify the qualification agent to adjust scoring criteria.

## 📊 API Reference

### Main Orchestrator
```python
from workflows.main_orchestrator import RoofingOutreachOrchestrator

orchestrator = RoofingOutreachOrchestrator()

# Run full workflow
result = await orchestrator.run_full_workflow("Miami, FL")

# Get campaign dashboard
dashboard = await orchestrator.get_campaign_dashboard(campaign_id)

# Process inbound response
response = await orchestrator.process_inbound_response("+1234567890", "Yes, interested!")
```

### Lead Qualification
```python
from agents.lead_qualification_agent import qualify_scraped_leads

# Qualify leads DataFrame
qualified_leads = await qualify_scraped_leads(leads_df)

# Get priority queue
priority_queue = await get_priority_outreach_queue(qualified_leads)
```

### Outreach Agent
```python
from agents.outreach_agent import OutreachAgent

agent = OutreachAgent()

# Send SMS
result = await agent.send_sms(lead_data, message)

# Make voice call
result = await agent.make_voice_call(lead_data, script)

# Schedule callback
result = await agent.schedule_callback(lead_data, datetime.now())
```

## 🔧 Deployment Options

### Docker Deployment (Recommended)
```bash
# Quick deployment
./deploy.sh

# Update deployment
./deploy.sh --update

# View logs
./deploy.sh --logs

# Create backup
./deploy.sh --backup
```

### Production Deployment

#### SSL Configuration
1. Obtain SSL certificates (Let's Encrypt recommended)
2. Update nginx configuration with SSL settings
3. Modify docker-compose.yml for HTTPS

#### Scaling
- Use Docker Swarm or Kubernetes for multi-node deployment
- Set up Redis cluster for high availability
- Configure load balancing for multiple agent instances

#### Monitoring
- Set up Prometheus metrics collection
- Configure alerting for system failures
- Monitor API rate limits and usage

## 🐛 Troubleshooting

### Common Issues

#### Scraping Issues
```bash
# Chrome/Chromium not found
export CHROME_BIN=/usr/bin/chromium-browser

# Permission issues
chmod +x deploy.sh
sudo chown -R $USER:$USER data logs
```

#### API Rate Limits
- Monitor usage in dashboard
- Adjust daily limits in .env file
- Implement exponential backoff

#### Database Connection
- Verify Supabase credentials
- Check network connectivity
- Review database logs

### Logs and Debugging
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f roofing-agent

# Debug mode
DEBUG=true docker-compose up
```

## 📈 Performance Optimization

### Scraping Performance
- Use headless browsers for better performance
- Implement caching for repeated requests
- Rotate user agents and proxies

### AI Model Performance
- Monitor response times in LangSmith
- Adjust model parameters for speed vs. accuracy
- Implement result caching

### Database Optimization
- Index frequently queried fields
- Implement connection pooling
- Regular database maintenance

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone https://github.com/your-username/roofing-outreach-agent.git

# Create development environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install
```

### Code Standards
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Include comprehensive docstrings
- Write tests for new features

### Testing
```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=. tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal and Ethical Considerations

### Terms of Service Compliance
- Respect platform terms of service for scraping
- Implement rate limiting and respectful scraping practices
- Consider using official APIs where available

### Data Privacy
- Implement GDPR compliance for EU users
- Provide opt-out mechanisms
- Secure storage of personal information

### Telecommunications Regulations
- Comply with TCPA regulations for automated calls/SMS
- Implement proper consent mechanisms
- Maintain do-not-call list compliance

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review logs for error details

## 🔄 Updates and Roadmap

### Version 1.0.0 Features
- ✅ Social media scraping (Facebook, Nextdoor)
- ✅ AI-powered lead qualification
- ✅ Multi-channel outreach (SMS, Voice, Calendar)
- ✅ Real-time dashboard and analytics
- ✅ Docker deployment

### Planned Features
- 🔄 Instagram and Twitter integration
- 🔄 Weather API integration for storm tracking
- 🔄 CRM integrations (Salesforce, HubSpot)
- 🔄 Advanced ML models for lead scoring
- 🔄 Mobile app for field teams

## 📊 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Social Media  │    │   AI Agents     │    │   Outreach      │
│   Scrapers      │    │                 │    │   Channels      │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Facebook      │───▶│ • Lead Qualify  │───▶│ • Twilio SMS    │
│ • Nextdoor      │    │ • Message Gen   │    │ • Voice Calls   │
│ • Location      │    │ • Priority      │    │ • Calendar      │
│   Targeting     │    │   Scoring       │    │   Scheduling    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Workflow Orchestrator                        │
├─────────────────────────────────────────────────────────────────┤
│ • Campaign Management  • Lead Tracking   • Performance Monitor │
│ • Automated Workflows  • Data Storage    • Error Handling      │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │    │   Analytics     │    │   Monitoring    │
│   (Supabase)    │    │   Dashboard     │    │   (LangSmith)   │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Leads Storage │    │ • Streamlit UI  │    │ • AI Performance│
│ • Campaign Data │    │ • Real-time     │    │ • Error Tracking│
│ • Outreach Log  │    │   Metrics       │    │ • Optimization  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

This system provides a complete solution for automated roofing lead generation and outreach, with AI-powered qualification and multi-channel communication capabilities.