import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import pandas as pd

from config.settings import settings


@dataclass
class LeadContact:
    """Contact information extracted from social media"""
    name: str
    platform: str
    location: str
    content: str
    timestamp: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class LeadQualificationResult(BaseModel):
    """Structured result from lead qualification"""
    lead_score: int = Field(description="Lead score from 1-100", ge=1, le=100)
    qualification_level: str = Field(description="hot, warm, or cold")
    urgency_level: str = Field(description="urgent, moderate, or low")
    damage_type: str = Field(description="Type of damage identified")
    estimated_project_value: str = Field(description="Estimated project value range")
    contact_preference: str = Field(description="Suggested contact method")
    qualification_notes: str = Field(description="Notes about this lead")
    follow_up_timeline: str = Field(description="When to follow up")
    objection_handling: List[str] = Field(description="Potential objections and responses")


class LeadQualificationAgent:
    """AI agent for qualifying roofing leads from social media"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(
            openai_api_key=settings.openai_api_key,
            model="gpt-4-1106-preview",
            temperature=0.1
        )
        self.output_parser = PydanticOutputParser(pydantic_object=LeadQualificationResult)
        
        self.qualification_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content="Lead Information:\n{lead_info}")
        ])
        
    def _get_system_prompt(self) -> str:
        """Get the system prompt for lead qualification"""
        return f"""
You are an expert roofing sales lead qualification agent for {settings.company_name}. 
Your job is to analyze social media posts and qualify potential roofing leads.

LEAD SCORING CRITERIA (1-100 scale):
- 90-100: HOT LEADS - Immediate need, specific damage mentioned, ready to hire
- 70-89: WARM LEADS - Damage reported, actively seeking help, good timing
- 50-69: WARM LEADS - Some damage indication, might be interested
- 30-49: COLD LEADS - General interest, no immediate need
- 1-29: POOR LEADS - Unlikely to convert

DAMAGE TYPE INDICATORS:
- Storm damage (hail, wind, tornado)
- Leak issues (water intrusion, missing shingles)
- Impact damage (tree fall, debris)
- Age-related issues (old roof, wear and tear)
- Insurance claims (adjuster involved, claim filed)

PROJECT VALUE ESTIMATION:
- Emergency repairs: $500-$3,000
- Partial roof replacement: $5,000-$15,000  
- Full roof replacement: $15,000-$50,000+
- Commercial projects: $25,000-$100,000+

URGENCY INDICATORS:
- Urgent: Active leaks, storm just passed, emergency language
- Moderate: Damage noticed, planning repairs, getting quotes
- Low: General maintenance, future planning

CONTACT PREFERENCES:
- Phone call: High urgency, immediate need
- SMS: Moderate urgency, initial contact
- Email: Low urgency, information gathering

Analyze each lead thoroughly and provide detailed qualification information.
Always consider the local market context and seasonal factors.

{self.output_parser.get_format_instructions()}
"""
    
    async def qualify_lead(self, lead_data: Dict) -> LeadQualificationResult:
        """Qualify a single lead from social media data"""
        try:
            # Format lead information for analysis
            lead_info = self._format_lead_info(lead_data)
            
            # Create the prompt
            messages = self.qualification_prompt.format_messages(lead_info=lead_info)
            
            # Get qualification from LLM
            response = await self.llm.agenerate([messages])
            result_text = response.generations[0][0].text
            
            # Parse the structured result
            qualification = self.output_parser.parse(result_text)
            
            self.logger.info(f"Qualified lead: {qualification.qualification_level} - Score: {qualification.lead_score}")
            return qualification
            
        except Exception as e:
            self.logger.error(f"Error qualifying lead: {e}")
            # Return default qualification on error
            return LeadQualificationResult(
                lead_score=25,
                qualification_level="cold",
                urgency_level="low",
                damage_type="unknown",
                estimated_project_value="$1,000-$5,000",
                contact_preference="email",
                qualification_notes=f"Error in qualification: {str(e)}",
                follow_up_timeline="1 week",
                objection_handling=["Price concerns", "Timing issues"]
            )
    
    def _format_lead_info(self, lead_data: Dict) -> str:
        """Format lead data for LLM analysis"""
        info_parts = []
        
        # Basic information
        info_parts.append(f"Platform: {lead_data.get('platform', 'Unknown')}")
        info_parts.append(f"Author: {lead_data.get('author', 'Unknown')}")
        info_parts.append(f"Location: {lead_data.get('neighborhood', lead_data.get('location', 'Unknown'))}")
        info_parts.append(f"Timestamp: {lead_data.get('timestamp', 'Unknown')}")
        
        # Content analysis
        content = lead_data.get('content', '')
        info_parts.append(f"\nPost Content:\n{content}")
        
        # Search context
        if 'search_keyword' in lead_data:
            info_parts.append(f"\nFound via keyword: {lead_data['search_keyword']}")
        
        # Existing potential assessment
        if 'potential_lead' in lead_data:
            potential = lead_data['potential_lead']
            if isinstance(potential, dict):
                info_parts.append(f"\nInitial Assessment:")
                info_parts.append(f"- Priority: {potential.get('priority', 'unknown')}")
                info_parts.append(f"- Total Score: {potential.get('total_score', 0)}")
        
        return "\n".join(info_parts)
    
    async def qualify_leads_batch(self, leads_df: pd.DataFrame) -> pd.DataFrame:
        """Qualify multiple leads in batch"""
        qualified_leads = []
        
        for index, lead_row in leads_df.iterrows():
            try:
                lead_data = lead_row.to_dict()
                qualification = await self.qualify_lead(lead_data)
                
                # Add qualification data to the lead
                lead_data.update({
                    'ai_lead_score': qualification.lead_score,
                    'ai_qualification_level': qualification.qualification_level,
                    'ai_urgency_level': qualification.urgency_level,
                    'ai_damage_type': qualification.damage_type,
                    'ai_project_value': qualification.estimated_project_value,
                    'ai_contact_preference': qualification.contact_preference,
                    'ai_qualification_notes': qualification.qualification_notes,
                    'ai_follow_up_timeline': qualification.follow_up_timeline,
                    'ai_objection_handling': qualification.objection_handling,
                    'qualified_at': datetime.now().isoformat()
                })
                
                qualified_leads.append(lead_data)
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error qualifying lead {index}: {e}")
                # Add the lead with minimal qualification
                lead_data = lead_row.to_dict()
                lead_data.update({
                    'ai_lead_score': 25,
                    'ai_qualification_level': 'cold',
                    'ai_urgency_level': 'low',
                    'ai_damage_type': 'unknown',
                    'ai_project_value': '$1,000-$5,000',
                    'ai_contact_preference': 'email',
                    'ai_qualification_notes': f'Qualification error: {str(e)}',
                    'ai_follow_up_timeline': '1 week',
                    'ai_objection_handling': ['Price concerns'],
                    'qualified_at': datetime.now().isoformat()
                })
                qualified_leads.append(lead_data)
        
        # Convert back to DataFrame and sort by lead score
        result_df = pd.DataFrame(qualified_leads)
        result_df = result_df.sort_values('ai_lead_score', ascending=False)
        
        self.logger.info(f"Qualified {len(result_df)} leads")
        return result_df
    
    async def extract_contact_info(self, lead_content: str) -> Dict[str, Optional[str]]:
        """Extract potential contact information from lead content"""
        
        contact_prompt = f"""
        Analyze this social media post and extract any potential contact information.
        Look for phone numbers, email addresses, or location details.
        
        Post content: {lead_content}
        
        Return a JSON object with:
        - phone: phone number if found (null if not found)
        - email: email address if found (null if not found)  
        - address: street address or specific location if found (null if not found)
        - location_hints: any location clues like neighborhood, landmarks, etc.
        
        Be conservative - only extract if you're confident it's contact information.
        """
        
        try:
            messages = [HumanMessage(content=contact_prompt)]
            response = await self.llm.agenerate([messages])
            result_text = response.generations[0][0].text
            
            # Simple parsing (in production, use structured output)
            import json
            try:
                contact_info = json.loads(result_text)
                return contact_info
            except json.JSONDecodeError:
                return {"phone": None, "email": None, "address": None, "location_hints": None}
                
        except Exception as e:
            self.logger.error(f"Error extracting contact info: {e}")
            return {"phone": None, "email": None, "address": None, "location_hints": None}
    
    def get_outreach_priority_queue(self, qualified_leads_df: pd.DataFrame) -> List[Dict]:
        """Get prioritized list of leads for outreach"""
        
        # Filter for leads worth contacting (score >= 40)
        contactable_leads = qualified_leads_df[qualified_leads_df['ai_lead_score'] >= 40].copy()
        
        # Create priority groups
        hot_leads = contactable_leads[contactable_leads['ai_qualification_level'] == 'hot']
        warm_leads = contactable_leads[contactable_leads['ai_qualification_level'] == 'warm']
        
        priority_queue = []
        
        # Add hot leads first (immediate contact)
        for _, lead in hot_leads.iterrows():
            priority_queue.append({
                'lead_data': lead.to_dict(),
                'priority': 'immediate',
                'suggested_contact_time': 'now',
                'contact_method': lead.get('ai_contact_preference', 'phone')
            })
        
        # Add urgent warm leads
        urgent_warm = warm_leads[warm_leads['ai_urgency_level'] == 'urgent']
        for _, lead in urgent_warm.iterrows():
            priority_queue.append({
                'lead_data': lead.to_dict(),
                'priority': 'high',
                'suggested_contact_time': 'within 2 hours',
                'contact_method': lead.get('ai_contact_preference', 'sms')
            })
        
        # Add other warm leads
        other_warm = warm_leads[warm_leads['ai_urgency_level'] != 'urgent']
        for _, lead in other_warm.iterrows():
            priority_queue.append({
                'lead_data': lead.to_dict(),
                'priority': 'medium',
                'suggested_contact_time': 'within 24 hours',
                'contact_method': lead.get('ai_contact_preference', 'sms')
            })
        
        self.logger.info(f"Created priority queue with {len(priority_queue)} leads")
        return priority_queue
    
    async def generate_personalized_message(self, lead_data: Dict, message_type: str = "initial") -> str:
        """Generate personalized outreach message"""
        
        message_prompt = f"""
        Generate a personalized {message_type} outreach message for this roofing lead.
        
        Lead Information:
        - Content: {lead_data.get('content', '')}
        - Platform: {lead_data.get('platform', '')}
        - Location: {lead_data.get('neighborhood', lead_data.get('location', ''))}
        - Damage Type: {lead_data.get('ai_damage_type', 'roof damage')}
        - Urgency: {lead_data.get('ai_urgency_level', 'moderate')}
        
        Company: {settings.company_name}
        Phone: {settings.business_phone}
        
        Message Guidelines:
        - Be helpful and empathetic
        - Reference their specific situation
        - Offer immediate value (free inspection)
        - Keep it conversational and local
        - Include call to action
        - Stay under 160 characters for SMS
        
        Generate a {message_type} message:
        """
        
        try:
            messages = [HumanMessage(content=message_prompt)]
            response = await self.llm.agenerate([messages])
            message = response.generations[0][0].text.strip()
            
            # Clean up any quotes or formatting
            message = message.strip('"').strip("'")
            
            return message
            
        except Exception as e:
            self.logger.error(f"Error generating message: {e}")
            # Fallback message
            return f"Hi! Saw your post about roof damage. {settings.company_name} offers free inspections in your area. Can we help? {settings.business_phone}"


# Utility functions
async def qualify_scraped_leads(leads_df: pd.DataFrame) -> pd.DataFrame:
    """Main function to qualify scraped leads"""
    agent = LeadQualificationAgent()
    qualified_leads = await agent.qualify_leads_batch(leads_df)
    return qualified_leads


async def get_priority_outreach_queue(qualified_leads_df: pd.DataFrame) -> List[Dict]:
    """Get prioritized outreach queue"""
    agent = LeadQualificationAgent()
    return agent.get_outreach_priority_queue(qualified_leads_df)


if __name__ == "__main__":
    # Test the agent
    async def main():
        # Sample lead data
        sample_leads = pd.DataFrame([
            {
                'platform': 'facebook',
                'author': 'John Smith',
                'content': 'Hurricane just passed and my roof has multiple missing shingles. Water is starting to leak into my living room. Need a roofer ASAP!',
                'location': 'Miami, FL',
                'timestamp': datetime.now().isoformat(),
                'potential_lead': {'priority': 'high', 'total_score': 8}
            },
            {
                'platform': 'nextdoor', 
                'author': 'Sarah Johnson',
                'content': 'Looking for recommendations for a good roofing contractor. Planning to replace our 15-year-old roof next spring.',
                'neighborhood': 'Coral Gables',
                'timestamp': datetime.now().isoformat(),
                'potential_lead': {'priority': 'medium', 'total_score': 5}
            }
        ])
        
        agent = LeadQualificationAgent()
        qualified = await agent.qualify_leads_batch(sample_leads)
        print("Qualified Leads:")
        print(qualified[['author', 'ai_lead_score', 'ai_qualification_level', 'ai_urgency_level']].to_string())
        
        # Get priority queue
        queue = agent.get_outreach_priority_queue(qualified)
        print(f"\nPriority Queue: {len(queue)} leads")
        for item in queue:
            print(f"- {item['priority']}: {item['lead_data']['author']} (Score: {item['lead_data']['ai_lead_score']})")
    
    asyncio.run(main())