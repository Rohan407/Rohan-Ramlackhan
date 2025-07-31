import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

from twilio.rest import Client
from twilio.twiml import MessagingResponse, VoiceResponse
import openai
from elevenlabs import generate, set_api_key
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import json
import httpx

from config.settings import settings


class OutreachChannel(Enum):
    SMS = "sms"
    VOICE = "voice"
    EMAIL = "email"


class OutreachStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RESPONDED = "responded"
    SCHEDULED = "scheduled"


@dataclass
class OutreachResult:
    """Result of an outreach attempt"""
    channel: OutreachChannel
    status: OutreachStatus
    message: str
    timestamp: datetime
    response_data: Optional[Dict] = None
    error: Optional[str] = None


class OutreachAgent:
    """Multi-channel AI-powered outreach agent for roofing leads"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize Twilio
        self.twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        
        # Initialize ElevenLabs
        set_api_key(settings.elevenlabs_api_key)
        
        # Initialize OpenAI
        openai.api_key = settings.openai_api_key
        
        # Track daily limits
        self.daily_sms_sent = 0
        self.daily_calls_made = 0
        
        # Google Calendar setup (if credentials exist)
        self.calendar_service = self._setup_google_calendar()
        
    def _setup_google_calendar(self):
        """Setup Google Calendar API"""
        try:
            # Load credentials from file
            from google.oauth2.service_account import Credentials
            
            credentials = Credentials.from_service_account_file(
                settings.google_credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            
            service = build('calendar', 'v3', credentials=credentials)
            self.logger.info("Google Calendar API initialized")
            return service
            
        except Exception as e:
            self.logger.warning(f"Could not initialize Google Calendar: {e}")
            return None
    
    async def send_sms(self, lead_data: Dict, message: str) -> OutreachResult:
        """Send SMS to a lead"""
        try:
            # Check daily limits
            if self.daily_sms_sent >= settings.max_daily_sms:
                return OutreachResult(
                    channel=OutreachChannel.SMS,
                    status=OutreachStatus.FAILED,
                    message=message,
                    timestamp=datetime.now(),
                    error="Daily SMS limit reached"
                )
            
            # Extract phone number (would need better extraction in production)
            phone_number = self._extract_phone_number(lead_data)
            if not phone_number:
                return OutreachResult(
                    channel=OutreachChannel.SMS,
                    status=OutreachStatus.FAILED,
                    message=message,
                    timestamp=datetime.now(),
                    error="No phone number available"
                )
            
            # Send SMS via Twilio
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=settings.twilio_phone_number,
                to=phone_number
            )
            
            self.daily_sms_sent += 1
            
            return OutreachResult(
                channel=OutreachChannel.SMS,
                status=OutreachStatus.SENT,
                message=message,
                timestamp=datetime.now(),
                response_data={
                    'message_sid': message_obj.sid,
                    'status': message_obj.status,
                    'to': phone_number
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error sending SMS: {e}")
            return OutreachResult(
                channel=OutreachChannel.SMS,
                status=OutreachStatus.FAILED,
                message=message,
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def make_voice_call(self, lead_data: Dict, script: str) -> OutreachResult:
        """Make an AI-powered voice call"""
        try:
            # Check daily limits and calling hours
            if self.daily_calls_made >= settings.max_daily_calls:
                return OutreachResult(
                    channel=OutreachChannel.VOICE,
                    status=OutreachStatus.FAILED,
                    message=script,
                    timestamp=datetime.now(),
                    error="Daily call limit reached"
                )
            
            if not self._is_calling_hours():
                return OutreachResult(
                    channel=OutreachChannel.VOICE,
                    status=OutreachStatus.FAILED,
                    message=script,
                    timestamp=datetime.now(),
                    error="Outside calling hours"
                )
            
            phone_number = self._extract_phone_number(lead_data)
            if not phone_number:
                return OutreachResult(
                    channel=OutreachChannel.VOICE,
                    status=OutreachStatus.FAILED,
                    message=script,
                    timestamp=datetime.now(),
                    error="No phone number available"
                )
            
            # Generate AI voice audio
            audio_content = await self._generate_voice_message(script, lead_data)
            
            # Create TwiML for the call
            twiml_url = await self._create_voice_twiml(script, audio_content)
            
            # Make the call
            call = self.twilio_client.calls.create(
                twiml=f'<Response><Play>{twiml_url}</Play></Response>',
                to=phone_number,
                from_=settings.twilio_phone_number
            )
            
            self.daily_calls_made += 1
            
            return OutreachResult(
                channel=OutreachChannel.VOICE,
                status=OutreachStatus.SENT,
                message=script,
                timestamp=datetime.now(),
                response_data={
                    'call_sid': call.sid,
                    'status': call.status,
                    'to': phone_number
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error making voice call: {e}")
            return OutreachResult(
                channel=OutreachChannel.VOICE,
                status=OutreachStatus.FAILED,
                message=script,
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def _generate_voice_message(self, script: str, lead_data: Dict) -> bytes:
        """Generate AI voice message using ElevenLabs"""
        try:
            # Personalize the script
            personalized_script = self._personalize_voice_script(script, lead_data)
            
            # Generate voice using ElevenLabs
            audio = generate(
                text=personalized_script,
                voice="Rachel",  # Professional female voice
                model="eleven_monolingual_v1"
            )
            
            return audio
            
        except Exception as e:
            self.logger.error(f"Error generating voice: {e}")
            # Return empty bytes on error
            return b""
    
    def _personalize_voice_script(self, script: str, lead_data: Dict) -> str:
        """Personalize voice script with lead information"""
        # Extract location for personalization
        location = lead_data.get('neighborhood', lead_data.get('location', 'your area'))
        author = lead_data.get('author', 'there')
        
        # Simple personalization
        personalized = script.replace('[NAME]', author)
        personalized = personalized.replace('[LOCATION]', location)
        personalized = personalized.replace('[COMPANY]', settings.company_name)
        
        return personalized
    
    async def _create_voice_twiml(self, script: str, audio_content: bytes) -> str:
        """Create TwiML URL for voice call (simplified)"""
        # In production, you'd upload the audio to a public URL
        # For now, return a simple TwiML with text-to-speech
        return f"<Response><Say voice='alice'>{script}</Say></Response>"
    
    def _extract_phone_number(self, lead_data: Dict) -> Optional[str]:
        """Extract phone number from lead data"""
        # Check if phone number was already extracted
        if 'phone' in lead_data and lead_data['phone']:
            return lead_data['phone']
        
        # For demo purposes, return a test number
        # In production, this would use more sophisticated extraction
        return "+1234567890"  # Test number
    
    def _is_calling_hours(self) -> bool:
        """Check if current time is within acceptable calling hours"""
        current_hour = datetime.now().hour
        return settings.call_hours_start <= current_hour <= settings.call_hours_end
    
    async def schedule_callback(self, lead_data: Dict, requested_time: datetime) -> OutreachResult:
        """Schedule a callback appointment"""
        try:
            if not self.calendar_service:
                return OutreachResult(
                    channel=OutreachChannel.EMAIL,
                    status=OutreachStatus.FAILED,
                    message="Calendar scheduling requested",
                    timestamp=datetime.now(),
                    error="Google Calendar not configured"
                )
            
            # Create calendar event
            event = {
                'summary': f'Roof Inspection Call - {lead_data.get("author", "Lead")}',
                'description': f'Follow-up call for roofing inquiry\n\nLead Details:\n{lead_data.get("content", "")}',
                'start': {
                    'dateTime': requested_time.isoformat(),
                    'timeZone': 'America/New_York',  # Adjust based on business location
                },
                'end': {
                    'dateTime': (requested_time + timedelta(minutes=30)).isoformat(),
                    'timeZone': 'America/New_York',
                },
                'attendees': [
                    {'email': 'sales@premiumroofingsolutions.com'},  # Business email
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }
            
            # Insert the event
            event_result = self.calendar_service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            return OutreachResult(
                channel=OutreachChannel.EMAIL,
                status=OutreachStatus.SCHEDULED,
                message=f"Callback scheduled for {requested_time}",
                timestamp=datetime.now(),
                response_data={
                    'event_id': event_result['id'],
                    'scheduled_time': requested_time.isoformat(),
                    'calendar_link': event_result.get('htmlLink')
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error scheduling callback: {e}")
            return OutreachResult(
                channel=OutreachChannel.EMAIL,
                status=OutreachStatus.FAILED,
                message="Calendar scheduling requested",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def execute_outreach_sequence(self, lead_data: Dict, sequence_config: Dict) -> List[OutreachResult]:
        """Execute a multi-step outreach sequence"""
        results = []
        
        try:
            # Step 1: Initial SMS (if high priority)
            if sequence_config.get('initial_sms', False):
                sms_message = sequence_config.get('sms_message', '')
                if sms_message:
                    sms_result = await self.send_sms(lead_data, sms_message)
                    results.append(sms_result)
                    
                    # Wait before next step
                    if sms_result.status == OutreachStatus.SENT:
                        await asyncio.sleep(sequence_config.get('sms_wait_minutes', 5) * 60)
            
            # Step 2: Voice call (if configured)
            if sequence_config.get('voice_call', False):
                call_script = sequence_config.get('call_script', '')
                if call_script:
                    call_result = await self.make_voice_call(lead_data, call_script)
                    results.append(call_result)
            
            # Step 3: Schedule follow-up (if requested)
            if sequence_config.get('schedule_followup', False):
                followup_time = datetime.now() + timedelta(
                    hours=sequence_config.get('followup_hours', 24)
                )
                schedule_result = await self.schedule_callback(lead_data, followup_time)
                results.append(schedule_result)
            
        except Exception as e:
            self.logger.error(f"Error in outreach sequence: {e}")
            results.append(OutreachResult(
                channel=OutreachChannel.SMS,
                status=OutreachStatus.FAILED,
                message="Sequence execution failed",
                timestamp=datetime.now(),
                error=str(e)
            ))
        
        return results
    
    def get_outreach_config(self, lead_priority: str, urgency: str) -> Dict:
        """Get outreach configuration based on lead priority and urgency"""
        
        configs = {
            'immediate_hot': {
                'initial_sms': True,
                'voice_call': True,
                'schedule_followup': True,
                'sms_message': "Hi! Saw your post about roof damage. We're a local roofing company and can help immediately. Can we call you in the next few minutes?",
                'call_script': "Hi [NAME], this is [COMPANY]. We saw your post about roof damage in [LOCATION] and want to help. We're offering free emergency inspections. Is now a good time to talk?",
                'sms_wait_minutes': 2,
                'followup_hours': 4
            },
            'high_urgent': {
                'initial_sms': True,
                'voice_call': False,
                'schedule_followup': True,
                'sms_message': "Hi! We specialize in storm damage repairs in [LOCATION]. Free inspection available today. Reply YES for immediate service.",
                'sms_wait_minutes': 15,
                'followup_hours': 8
            },
            'medium_warm': {
                'initial_sms': True,
                'voice_call': False,
                'schedule_followup': True,
                'sms_message': "Hi [NAME]! Saw your roofing inquiry. [COMPANY] offers free inspections in [LOCATION]. When's a good time to call?",
                'sms_wait_minutes': 30,
                'followup_hours': 24
            },
            'low_cold': {
                'initial_sms': True,
                'voice_call': False,
                'schedule_followup': False,
                'sms_message': "Hi! [COMPANY] offers roofing services in [LOCATION]. Free estimates available. Let us know if you need help!",
                'sms_wait_minutes': 60,
                'followup_hours': 72
            }
        }
        
        # Determine config key
        if lead_priority == 'immediate' or urgency == 'urgent':
            config_key = 'immediate_hot'
        elif lead_priority == 'high':
            config_key = 'high_urgent'
        elif lead_priority == 'medium':
            config_key = 'medium_warm'
        else:
            config_key = 'low_cold'
        
        return configs.get(config_key, configs['low_cold'])
    
    async def handle_inbound_sms(self, message_body: str, from_number: str) -> str:
        """Handle inbound SMS responses"""
        try:
            # Simple response logic
            message_lower = message_body.lower().strip()
            
            if any(word in message_lower for word in ['yes', 'interested', 'call', 'help']):
                return f"Great! A {settings.company_name} specialist will call you within the hour. For urgent needs, call {settings.business_phone}"
            
            elif any(word in message_lower for word in ['no', 'stop', 'unsubscribe']):
                return "Understood. We've removed you from our list. If you need roofing help in the future, feel free to reach out!"
            
            elif any(word in message_lower for word in ['when', 'time', 'schedule']):
                return f"We can call anytime Mon-Fri 9AM-6PM. Reply with your preferred time or call {settings.business_phone}"
            
            else:
                return f"Thanks for your message! A {settings.company_name} representative will respond shortly. For immediate help: {settings.business_phone}"
                
        except Exception as e:
            self.logger.error(f"Error handling inbound SMS: {e}")
            return f"Thanks for your message! For immediate assistance, call {settings.business_phone}"
    
    def get_daily_stats(self) -> Dict:
        """Get daily outreach statistics"""
        return {
            'sms_sent': self.daily_sms_sent,
            'calls_made': self.daily_calls_made,
            'sms_remaining': settings.max_daily_sms - self.daily_sms_sent,
            'calls_remaining': settings.max_daily_calls - self.daily_calls_made,
            'is_calling_hours': self._is_calling_hours()
        }


# Utility functions
async def execute_priority_outreach(priority_queue: List[Dict]) -> List[Dict]:
    """Execute outreach for priority queue"""
    agent = OutreachAgent()
    outreach_results = []
    
    for queue_item in priority_queue:
        lead_data = queue_item['lead_data']
        priority = queue_item['priority']
        
        # Get outreach configuration
        urgency = lead_data.get('ai_urgency_level', 'moderate')
        config = agent.get_outreach_config(priority, urgency)
        
        # Execute outreach sequence
        results = await agent.execute_outreach_sequence(lead_data, config)
        
        outreach_results.append({
            'lead_id': f"{lead_data.get('platform')}_{lead_data.get('author')}",
            'lead_data': lead_data,
            'priority': priority,
            'outreach_results': results,
            'executed_at': datetime.now().isoformat()
        })
        
        # Rate limiting between leads
        await asyncio.sleep(10)
    
    return outreach_results


if __name__ == "__main__":
    # Test the outreach agent
    async def main():
        agent = OutreachAgent()
        
        # Sample lead data
        sample_lead = {
            'platform': 'facebook',
            'author': 'John Smith',
            'content': 'Hurricane damaged my roof, water leaking badly!',
            'location': 'Miami, FL',
            'ai_urgency_level': 'urgent',
            'phone': '+1234567890'  # Test number
        }
        
        # Test SMS
        sms_result = await agent.send_sms(
            sample_lead, 
            "Hi John! Saw your post about roof damage. We can help immediately. Free inspection available today!"
        )
        print(f"SMS Result: {sms_result.status} - {sms_result.message}")
        
        # Get daily stats
        stats = agent.get_daily_stats()
        print(f"Daily Stats: {stats}")
    
    asyncio.run(main())