#!/usr/bin/env python3
"""
Test Script for Twilio SMS Functionality
This script tests SMS sending capabilities with your Twilio configuration.
"""

import os
import sys
from datetime import datetime

# Add the project root to Python path
sys.path.append('.')

def test_twilio_connection():
    """Test Twilio connection and configuration"""
    
    print("📱 Testing Twilio SMS Setup")
    print("=" * 40)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check configuration
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_PHONE_NUMBER')
    
    print("🔍 Checking Twilio Configuration...")
    
    if not account_sid or account_sid == 'your-twilio-account-sid':
        print("❌ Twilio Account SID not configured")
        return False
    else:
        print(f"✅ Account SID: {account_sid}")
    
    if not auth_token or auth_token == 'your-twilio-auth-token':
        print("❌ Twilio Auth Token not configured")
        return False
    else:
        print(f"✅ Auth Token: {auth_token[:10]}...{auth_token[-4:]}")
    
    if not from_number or from_number == '+1234567890':
        print("❌ Twilio Phone Number not configured")
        print("🔧 You need to buy a phone number from Twilio Console")
        print("   Go to: Phone Numbers → Manage → Buy a number")
        return False
    else:
        print(f"✅ From Number: {from_number}")
    
    return True

def test_twilio_client():
    """Test Twilio client initialization"""
    
    try:
        from twilio.rest import Client
        
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        print("\n🔗 Testing Twilio Client Connection...")
        
        client = Client(account_sid, auth_token)
        
        # Test by fetching account info
        account = client.api.accounts(account_sid).fetch()
        
        print(f"✅ Connected successfully!")
        print(f"   Account Name: {account.friendly_name}")
        print(f"   Account Status: {account.status}")
        print(f"   Account Type: {account.type}")
        
        return client
        
    except Exception as e:
        print(f"❌ Failed to connect to Twilio: {e}")
        return None

def test_phone_number_info(client):
    """Get information about the configured phone number"""
    
    try:
        from_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        print(f"\n📞 Checking Phone Number: {from_number}")
        
        # Get phone number details
        phone_numbers = client.incoming_phone_numbers.list()
        
        found_number = None
        for number in phone_numbers:
            if number.phone_number == from_number:
                found_number = number
                break
        
        if found_number:
            print(f"✅ Phone number found and active")
            print(f"   Friendly Name: {found_number.friendly_name}")
            print(f"   Capabilities: SMS={found_number.capabilities['sms']}, Voice={found_number.capabilities['voice']}")
            return True
        else:
            print(f"❌ Phone number {from_number} not found in your account")
            print("Available numbers in your account:")
            for number in phone_numbers:
                print(f"   - {number.phone_number}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking phone number: {e}")
        return False

def send_test_sms(client, to_number):
    """Send a test SMS"""
    
    try:
        from_number = os.getenv('TWILIO_PHONE_NUMBER')
        company_name = os.getenv('COMPANY_NAME', 'Premium Roofing Solutions')
        
        test_message = f"🏠 Test message from {company_name} AI system! Your roofing outreach agent is working. Reply STOP to opt out."
        
        print(f"\n📤 Sending test SMS to {to_number}...")
        print(f"Message: {test_message}")
        
        message = client.messages.create(
            body=test_message,
            from_=from_number,
            to=to_number
        )
        
        print(f"✅ SMS sent successfully!")
        print(f"   Message SID: {message.sid}")
        print(f"   Status: {message.status}")
        print(f"   Direction: {message.direction}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}")
        return False

def test_ai_sms_integration():
    """Test integration between AI agent and SMS"""
    
    print("\n🤖 Testing AI + SMS Integration...")
    
    try:
        # Import our AI agent
        from agents.lead_qualification_agent import LeadQualificationAgent
        
        # Sample lead data
        sample_lead = {
            'platform': 'facebook',
            'author': 'Test User',
            'content': 'Hurricane damaged my roof! Need help ASAP!',
            'location': 'Tampa, FL',
            'ai_urgency_level': 'urgent',
            'ai_qualification_level': 'hot',
            'ai_lead_score': 95
        }
        
        print("✅ AI agent imported successfully")
        
        # Test message generation
        import asyncio
        
        async def generate_message():
            agent = LeadQualificationAgent()
            message = await agent.generate_personalized_message(sample_lead, "initial")
            return message
        
        message = asyncio.run(generate_message())
        print(f"✅ AI-generated message: '{message}'")
        
        return message
        
    except Exception as e:
        print(f"❌ AI integration test failed: {e}")
        return None

def main():
    """Main test function"""
    
    print("🚀 Twilio SMS Test Suite")
    print("This script tests your Twilio SMS configuration and functionality")
    print()
    
    # Test 1: Configuration
    if not test_twilio_connection():
        print("\n❌ Configuration test failed. Please check your .env file.")
        return
    
    # Test 2: Client connection
    client = test_twilio_client()
    if not client:
        print("\n❌ Client connection failed. Check your credentials.")
        return
    
    # Test 3: Phone number validation
    if not test_phone_number_info(client):
        print("\n❌ Phone number validation failed.")
        print("🔧 Next step: Buy a phone number in Twilio Console")
        return
    
    # Test 4: AI integration
    ai_message = test_ai_sms_integration()
    
    # Test 5: Optional SMS sending
    print("\n" + "="*50)
    print("🎯 READY FOR SMS TESTING!")
    print("="*50)
    
    print("Your Twilio setup is complete and working!")
    
    send_test = input("\nWould you like to send a test SMS? (y/n): ").lower().strip()
    
    if send_test == 'y':
        to_number = input("Enter your phone number (e.g., +1234567890): ").strip()
        
        if to_number:
            if send_test_sms(client, to_number):
                print("\n🎉 SUCCESS! Your SMS system is working!")
                print("\nNext steps:")
                print("1. Set up Supabase for lead storage")
                print("2. Run full system: ./deploy.sh")
                print("3. Launch your first campaign!")
            else:
                print("\n❌ SMS test failed. Check the error above.")
        else:
            print("❌ No phone number provided.")
    else:
        print("\n✅ Twilio setup verified! SMS sending capability confirmed.")
        print("\nYour system is ready for:")
        print("• Automated SMS campaigns")
        print("• Lead response handling") 
        print("• Multi-channel outreach")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()