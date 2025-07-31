#!/usr/bin/env python3
"""
Test Script for AI Lead Qualification
This script demonstrates the AI lead qualification functionality using only OpenAI API.
Perfect for testing before setting up other services.
"""

import asyncio
import pandas as pd
from datetime import datetime
import os
import sys

# Add the project root to Python path
sys.path.append('.')

from agents.lead_qualification_agent import LeadQualificationAgent

# Test data - simulate scraped leads
SAMPLE_LEADS = [
    {
        'platform': 'facebook',
        'author': 'John Smith',
        'content': 'Hurricane Milton just passed through and my roof has multiple missing shingles! Water is starting to leak into my living room. Need a roofer ASAP! Insurance adjuster coming tomorrow.',
        'location': 'Tampa, FL',
        'timestamp': datetime.now().isoformat(),
        'search_keyword': 'roof damage',
        'potential_lead': {'priority': 'high', 'total_score': 8}
    },
    {
        'platform': 'nextdoor', 
        'author': 'Sarah Johnson',
        'content': 'Looking for recommendations for a good roofing contractor. Our 15-year-old roof held up during the storm but we noticed some loose shingles. Planning to get it inspected and possibly replaced next spring.',
        'location': 'Tampa, FL',
        'neighborhood': 'Hyde Park',
        'timestamp': datetime.now().isoformat(),
        'search_keyword': 'roofing contractor',
        'potential_lead': {'priority': 'medium', 'total_score': 5}
    },
    {
        'platform': 'facebook',
        'author': 'Mike Wilson', 
        'content': 'OMG! Tree fell directly on our roof during the storm! Huge hole in the bedroom ceiling and rain is pouring in. This is an emergency! Anyone know a 24/7 roofing service? Insurance company said call immediately.',
        'location': 'St. Petersburg, FL',
        'timestamp': datetime.now().isoformat(),
        'search_keyword': 'tree fell on roof',
        'potential_lead': {'priority': 'high', 'total_score': 10}
    },
    {
        'platform': 'nextdoor',
        'author': 'Lisa Davis',
        'content': 'Hi neighbors! We\'re thinking about updating our roof sometime in the future. It\'s about 10 years old and still in decent shape, but we want to start getting quotes for budgeting purposes.',
        'location': 'Clearwater, FL', 
        'neighborhood': 'Countryside',
        'timestamp': datetime.now().isoformat(),
        'search_keyword': 'roof update',
        'potential_lead': {'priority': 'low', 'total_score': 3}
    },
    {
        'platform': 'facebook',
        'author': 'Tom Rodriguez',
        'content': 'Storm damaged our gutters and we noticed some shingles in the yard. Not sure how bad the roof damage is but definitely need someone to come take a look. Hoping insurance will cover it.',
        'location': 'Tampa, FL',
        'timestamp': datetime.now().isoformat(), 
        'search_keyword': 'storm damage',
        'potential_lead': {'priority': 'medium', 'total_score': 6}
    }
]

async def test_ai_qualification():
    """Test the AI lead qualification system"""
    
    print("🏠 Testing Roofing AI Lead Qualification System")
    print("=" * 50)
    
    # Check if OpenAI API key is configured
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key or openai_key == 'sk-your-openai-api-key-here':
        print("❌ Error: OpenAI API key not found in environment variables")
        print("Please set OPENAI_API_KEY in your .env file or environment")
        return
    
    print(f"✅ OpenAI API key configured: {openai_key[:20]}...")
    print()
    
    # Create sample DataFrame
    leads_df = pd.DataFrame(SAMPLE_LEADS)
    print(f"📊 Testing with {len(leads_df)} sample leads:")
    
    for i, lead in enumerate(SAMPLE_LEADS, 1):
        print(f"  {i}. {lead['author']} - {lead['potential_lead']['priority']} priority")
    
    print("\n🤖 Starting AI qualification...")
    print("-" * 40)
    
    try:
        # Initialize the AI agent
        agent = LeadQualificationAgent()
        
        # Test individual lead qualification
        print("\n🔍 Individual Lead Analysis:")
        for i, lead_data in enumerate(SAMPLE_LEADS[:3], 1):  # Test first 3 leads
            print(f"\n--- Lead {i}: {lead_data['author']} ---")
            print(f"Content: {lead_data['content'][:100]}...")
            
            try:
                qualification = await agent.qualify_lead(lead_data)
                
                print(f"🎯 AI Score: {qualification.lead_score}/100")
                print(f"📊 Level: {qualification.qualification_level.upper()}")
                print(f"⏰ Urgency: {qualification.urgency_level}")
                print(f"🏠 Damage Type: {qualification.damage_type}")
                print(f"💰 Project Value: {qualification.estimated_project_value}")
                print(f"📞 Contact Method: {qualification.contact_preference}")
                print(f"📝 Notes: {qualification.qualification_notes[:100]}...")
                
            except Exception as e:
                print(f"❌ Error qualifying lead: {e}")
        
        # Test batch qualification
        print(f"\n🚀 Batch Processing All {len(leads_df)} Leads...")
        
        qualified_leads_df = await agent.qualify_leads_batch(leads_df)
        
        print("\n📈 Qualification Results Summary:")
        print("=" * 40)
        
        # Summary statistics
        total_leads = len(qualified_leads_df)
        hot_leads = len(qualified_leads_df[qualified_leads_df['ai_qualification_level'] == 'hot'])
        warm_leads = len(qualified_leads_df[qualified_leads_df['ai_qualification_level'] == 'warm']) 
        cold_leads = len(qualified_leads_df[qualified_leads_df['ai_qualification_level'] == 'cold'])
        avg_score = qualified_leads_df['ai_lead_score'].mean()
        
        print(f"📊 Total Leads Processed: {total_leads}")
        print(f"🔥 Hot Leads: {hot_leads} ({hot_leads/total_leads*100:.1f}%)")
        print(f"🔸 Warm Leads: {warm_leads} ({warm_leads/total_leads*100:.1f}%)")
        print(f"❄️  Cold Leads: {cold_leads} ({cold_leads/total_leads*100:.1f}%)")
        print(f"⭐ Average Score: {avg_score:.1f}/100")
        
        # Show top leads
        print(f"\n🏆 Top Qualified Leads:")
        top_leads = qualified_leads_df.nlargest(3, 'ai_lead_score')
        
        for i, (_, lead) in enumerate(top_leads.iterrows(), 1):
            print(f"  {i}. {lead['author']} - Score: {lead['ai_lead_score']}/100 ({lead['ai_qualification_level']})")
            print(f"     📱 Contact via: {lead['ai_contact_preference']}")
            print(f"     💰 Est. Value: {lead['ai_project_value']}")
            print()
        
        # Test priority queue creation
        print("🎯 Creating Priority Outreach Queue...")
        priority_queue = agent.get_outreach_priority_queue(qualified_leads_df)
        
        print(f"📞 {len(priority_queue)} leads ready for outreach:")
        for item in priority_queue:
            lead_data = item['lead_data']
            print(f"  • {lead_data['author']} - {item['priority']} priority - {item['contact_method']}")
        
        # Test message generation
        print(f"\n💬 Testing AI Message Generation...")
        if priority_queue:
            top_lead = priority_queue[0]['lead_data']
            message = await agent.generate_personalized_message(top_lead, "initial")
            print(f"Sample SMS for {top_lead['author']}:")
            print(f"'{message}'")
        
        print(f"\n✅ AI Testing Complete!")
        print(f"🎉 Your AI qualification system is working perfectly!")
        print(f"\nNext steps:")
        print(f"1. Set up Supabase for data storage")
        print(f"2. Set up Twilio for SMS outreach") 
        print(f"3. Run the full system: ./deploy.sh")
        
    except Exception as e:
        print(f"❌ Error during AI testing: {e}")
        print(f"Check your OpenAI API key and internet connection")
        import traceback
        traceback.print_exc()

async def test_message_generation():
    """Test personalized message generation"""
    print("\n💬 Testing Message Generation")
    print("-" * 30)
    
    agent = LeadQualificationAgent()
    
    for lead_data in SAMPLE_LEADS[:2]:
        message = await agent.generate_personalized_message(lead_data, "initial")
        print(f"\n📱 Message for {lead_data['author']}:")
        print(f"Content: {lead_data['content'][:50]}...")
        print(f"Generated: '{message}'")

if __name__ == "__main__":
    print("🚀 Starting AI Lead Qualification Test")
    print("This test uses only your OpenAI API key")
    print()
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        asyncio.run(test_ai_qualification())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()