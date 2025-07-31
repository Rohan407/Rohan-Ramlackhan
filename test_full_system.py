#!/usr/bin/env python3
"""
Full System Test Script
Tests all configured APIs and core functionality of the Roofing Outreach AI system.
"""

import asyncio
import os
import sys
from datetime import datetime
import pandas as pd

# Add the project root to Python path
sys.path.append('.')

def load_environment():
    """Load environment variables"""
    from dotenv import load_dotenv
    load_dotenv()

def test_api_configurations():
    """Test all API configurations"""
    
    print("🔍 Testing API Configurations")
    print("=" * 40)
    
    configs = {}
    
    # OpenAI
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key and openai_key.startswith('sk-'):
        print("✅ OpenAI API Key configured")
        configs['openai'] = True
    else:
        print("❌ OpenAI API Key missing")
        configs['openai'] = False
    
    # Twilio
    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')
    
    if all([twilio_sid, twilio_token, twilio_phone]) and twilio_phone != '+1234567890':
        print("✅ Twilio fully configured")
        configs['twilio'] = True
    else:
        print("❌ Twilio incomplete")
        configs['twilio'] = False
    
    # ElevenLabs
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')
    if elevenlabs_key and elevenlabs_key.startswith('sk_'):
        print("✅ ElevenLabs API Key configured")
        configs['elevenlabs'] = True
    else:
        print("❌ ElevenLabs API Key missing")
        configs['elevenlabs'] = False
    
    # Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if all([supabase_url, supabase_key]) and 'supabase.co' in supabase_url:
        print("✅ Supabase configured")
        configs['supabase'] = True
    else:
        print("❌ Supabase incomplete")
        configs['supabase'] = False
    
    # LangSmith
    langsmith_key = os.getenv('LANGSMITH_API_KEY')
    if langsmith_key and langsmith_key != 'your-langsmith-api-key':
        print("✅ LangSmith configured")
        configs['langsmith'] = True
    else:
        print("🔶 LangSmith not configured (optional)")
        configs['langsmith'] = False
    
    return configs

async def test_ai_qualification():
    """Test AI lead qualification"""
    
    print("\n🤖 Testing AI Lead Qualification")
    print("-" * 30)
    
    try:
        from agents.lead_qualification_agent import LeadQualificationAgent
        
        # Sample lead
        sample_lead = {
            'platform': 'facebook',
            'author': 'Test User',
            'content': 'Hurricane just passed and my roof has major damage! Shingles everywhere and water leaking into bedroom. Need emergency roofing service ASAP! Insurance adjuster coming tomorrow.',
            'location': 'Tampa, FL',
            'timestamp': datetime.now().isoformat(),
            'potential_lead': {'priority': 'high', 'total_score': 9}
        }
        
        agent = LeadQualificationAgent()
        qualification = await agent.qualify_lead(sample_lead)
        
        print(f"✅ AI Qualification successful!")
        print(f"   Score: {qualification.lead_score}/100")
        print(f"   Level: {qualification.qualification_level}")
        print(f"   Urgency: {qualification.urgency_level}")
        print(f"   Damage Type: {qualification.damage_type}")
        print(f"   Project Value: {qualification.estimated_project_value}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI Qualification failed: {e}")
        return False

async def test_database_connection():
    """Test Supabase database connection"""
    
    print("\n💾 Testing Database Connection")
    print("-" * 30)
    
    try:
        from api.database_manager import DatabaseManager
        
        db = DatabaseManager()
        
        # Test connection by creating tables
        await db.create_tables()
        print("✅ Database connection successful!")
        print("✅ Tables created/verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_twilio_connection():
    """Test Twilio connection"""
    
    print("\n📱 Testing Twilio Connection")
    print("-" * 30)
    
    try:
        from twilio.rest import Client
        
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        client = Client(account_sid, auth_token)
        account = client.api.accounts(account_sid).fetch()
        
        print(f"✅ Twilio connection successful!")
        print(f"   Account: {account.friendly_name}")
        print(f"   Status: {account.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Twilio connection failed: {e}")
        return False

def test_elevenlabs_connection():
    """Test ElevenLabs connection"""
    
    print("\n🎤 Testing ElevenLabs Connection")
    print("-" * 30)
    
    try:
        import requests
        
        api_key = os.getenv('ELEVENLABS_API_KEY')
        
        headers = {
            'Accept': 'application/json',
            'xi-api-key': api_key
        }
        
        response = requests.get('https://api.elevenlabs.io/v1/user', headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ ElevenLabs connection successful!")
            print(f"   Characters available: {user_data.get('subscription', {}).get('character_count', 'Unknown')}")
            return True
        else:
            print(f"❌ ElevenLabs connection failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ ElevenLabs connection failed: {e}")
        return False

async def test_outreach_agent():
    """Test outreach agent functionality"""
    
    print("\n📞 Testing Outreach Agent")
    print("-" * 30)
    
    try:
        from agents.outreach_agent import OutreachAgent
        
        agent = OutreachAgent()
        
        # Test message generation (no actual sending)
        sample_lead = {
            'author': 'John Smith',
            'content': 'Storm damaged my roof!',
            'location': 'Tampa, FL',
            'ai_urgency_level': 'urgent',
            'ai_lead_score': 95
        }
        
        # Get daily stats
        stats = agent.get_daily_stats()
        print(f"✅ Outreach agent initialized successfully!")
        print(f"   SMS capacity: {stats['sms_remaining']}/{stats['sms_remaining'] + stats['sms_sent']}")
        print(f"   Call capacity: {stats['calls_remaining']}/{stats['calls_remaining'] + stats['calls_made']}")
        print(f"   Within calling hours: {stats['is_calling_hours']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Outreach agent test failed: {e}")
        return False

async def test_workflow_orchestrator():
    """Test main workflow orchestrator"""
    
    print("\n🎯 Testing Workflow Orchestrator")
    print("-" * 30)
    
    try:
        from workflows.main_orchestrator import RoofingOutreachOrchestrator
        
        orchestrator = RoofingOutreachOrchestrator()
        
        print("✅ Workflow orchestrator initialized successfully!")
        print("✅ Ready for campaign management")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow orchestrator test failed: {e}")
        return False

async def run_comprehensive_test():
    """Run comprehensive system test"""
    
    print("🚀 Roofing Outreach AI - Full System Test")
    print("=" * 50)
    print()
    
    load_environment()
    
    # Test configurations
    configs = test_api_configurations()
    
    # Test individual components
    test_results = {}
    
    if configs['openai']:
        test_results['ai_qualification'] = await test_ai_qualification()
    else:
        test_results['ai_qualification'] = False
    
    if configs['supabase']:
        test_results['database'] = await test_database_connection()
    else:
        test_results['database'] = False
    
    if configs['twilio']:
        test_results['twilio'] = test_twilio_connection()
    else:
        test_results['twilio'] = False
    
    if configs['elevenlabs']:
        test_results['elevenlabs'] = test_elevenlabs_connection()
    else:
        test_results['elevenlabs'] = False
    
    test_results['outreach_agent'] = await test_outreach_agent()
    test_results['orchestrator'] = await test_workflow_orchestrator()
    
    # Results summary
    print("\n" + "=" * 50)
    print("🎯 SYSTEM TEST RESULTS")
    print("=" * 50)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    print(f"📊 Overall: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
    print()
    
    for component, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {component.replace('_', ' ').title()}")
    
    # System readiness assessment
    print("\n🎯 SYSTEM READINESS:")
    
    if test_results['ai_qualification'] and test_results['database']:
        print("✅ CORE SYSTEM READY - Can qualify leads and store data")
    
    if test_results['twilio']:
        print("✅ SMS OUTREACH READY - Can send messages to leads")
    
    if test_results['elevenlabs']:
        print("✅ VOICE OUTREACH READY - Can make AI voice calls")
    
    if all([test_results['ai_qualification'], test_results['database'], test_results['twilio']]):
        print("\n🎉 FULL SYSTEM OPERATIONAL!")
        print("Ready to launch your first roofing campaign!")
        print("\nNext steps:")
        print("1. Run: ./deploy.sh")
        print("2. Access dashboard: http://localhost")
        print("3. Create your first campaign!")
    else:
        print("\n🔧 SYSTEM NEEDS ATTENTION:")
        if not test_results['ai_qualification']:
            print("- Fix OpenAI API configuration")
        if not test_results['database']:
            print("- Fix Supabase configuration")
        if not test_results['twilio']:
            print("- Fix Twilio configuration")

def main():
    """Main test function"""
    
    try:
        asyncio.run(run_comprehensive_test())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()