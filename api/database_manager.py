import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging
import json

from supabase import create_client, Client
import pandas as pd
from config.settings import settings


class DatabaseManager:
    """Manager for Supabase database operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
        
    async def create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            # Leads table
            leads_table = """
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                platform VARCHAR(50) NOT NULL,
                author VARCHAR(255),
                content TEXT,
                location VARCHAR(255),
                neighborhood VARCHAR(255),
                timestamp TIMESTAMP,
                search_keyword VARCHAR(255),
                phone VARCHAR(20),
                email VARCHAR(255),
                address TEXT,
                ai_lead_score INTEGER,
                ai_qualification_level VARCHAR(20),
                ai_urgency_level VARCHAR(20),
                ai_damage_type VARCHAR(100),
                ai_project_value VARCHAR(50),
                ai_contact_preference VARCHAR(20),
                ai_qualification_notes TEXT,
                ai_follow_up_timeline VARCHAR(50),
                ai_objection_handling JSONB,
                potential_lead JSONB,
                qualified_at TIMESTAMP,
                scraped_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
            
            # Outreach attempts table
            outreach_table = """
            CREATE TABLE IF NOT EXISTS outreach_attempts (
                id SERIAL PRIMARY KEY,
                lead_id INTEGER REFERENCES leads(id),
                channel VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL,
                message TEXT,
                response_data JSONB,
                error_message TEXT,
                attempt_timestamp TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            );
            """
            
            # Lead status tracking
            lead_status_table = """
            CREATE TABLE IF NOT EXISTS lead_status (
                id SERIAL PRIMARY KEY,
                lead_id INTEGER REFERENCES leads(id),
                status VARCHAR(50) NOT NULL,
                notes TEXT,
                next_action VARCHAR(100),
                next_action_date TIMESTAMP,
                assigned_to VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
            
            # Campaigns table for tracking different storm events
            campaigns_table = """
            CREATE TABLE IF NOT EXISTS campaigns (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                storm_location VARCHAR(255),
                storm_date DATE,
                zip_codes JSONB,
                status VARCHAR(50) DEFAULT 'active',
                total_leads INTEGER DEFAULT 0,
                qualified_leads INTEGER DEFAULT 0,
                contacted_leads INTEGER DEFAULT 0,
                converted_leads INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
            
            self.logger.info("Database tables created successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating tables: {e}")
    
    async def save_leads(self, leads_df: pd.DataFrame, campaign_id: Optional[int] = None) -> List[int]:
        """Save scraped leads to database"""
        try:
            lead_ids = []
            
            for _, lead_row in leads_df.iterrows():
                lead_data = lead_row.to_dict()
                
                # Clean up data types
                lead_record = {
                    'platform': lead_data.get('platform'),
                    'author': lead_data.get('author'),
                    'content': lead_data.get('content'),
                    'location': lead_data.get('location'),
                    'neighborhood': lead_data.get('neighborhood'),
                    'timestamp': lead_data.get('timestamp'),
                    'search_keyword': lead_data.get('search_keyword'),
                    'phone': lead_data.get('phone'),
                    'email': lead_data.get('email'),
                    'address': lead_data.get('address'),
                    'ai_lead_score': lead_data.get('ai_lead_score'),
                    'ai_qualification_level': lead_data.get('ai_qualification_level'),
                    'ai_urgency_level': lead_data.get('ai_urgency_level'),
                    'ai_damage_type': lead_data.get('ai_damage_type'),
                    'ai_project_value': lead_data.get('ai_project_value'),
                    'ai_contact_preference': lead_data.get('ai_contact_preference'),
                    'ai_qualification_notes': lead_data.get('ai_qualification_notes'),
                    'ai_follow_up_timeline': lead_data.get('ai_follow_up_timeline'),
                    'ai_objection_handling': lead_data.get('ai_objection_handling'),
                    'potential_lead': lead_data.get('potential_lead'),
                    'qualified_at': lead_data.get('qualified_at'),
                    'scraped_at': lead_data.get('scraped_at'),
                    'campaign_id': campaign_id
                }
                
                # Remove None values
                lead_record = {k: v for k, v in lead_record.items() if v is not None}
                
                # Insert lead
                result = self.supabase.table('leads').insert(lead_record).execute()
                
                if result.data:
                    lead_id = result.data[0]['id']
                    lead_ids.append(lead_id)
                    
                    # Create initial status record
                    await self.update_lead_status(
                        lead_id,
                        'new',
                        'Lead scraped and qualified',
                        'contact_outreach'
                    )
            
            self.logger.info(f"Saved {len(lead_ids)} leads to database")
            return lead_ids
            
        except Exception as e:
            self.logger.error(f"Error saving leads: {e}")
            return []
    
    async def save_outreach_attempt(self, lead_id: int, outreach_result) -> bool:
        """Save outreach attempt to database"""
        try:
            attempt_data = {
                'lead_id': lead_id,
                'channel': outreach_result.channel.value,
                'status': outreach_result.status.value,
                'message': outreach_result.message,
                'response_data': outreach_result.response_data,
                'error_message': outreach_result.error,
                'attempt_timestamp': outreach_result.timestamp.isoformat()
            }
            
            result = self.supabase.table('outreach_attempts').insert(attempt_data).execute()
            
            if result.data:
                self.logger.info(f"Saved outreach attempt for lead {lead_id}")
                return True
            else:
                self.logger.error(f"Failed to save outreach attempt for lead {lead_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving outreach attempt: {e}")
            return False
    
    async def update_lead_status(self, lead_id: int, status: str, notes: str = None, next_action: str = None) -> bool:
        """Update lead status"""
        try:
            status_data = {
                'lead_id': lead_id,
                'status': status,
                'notes': notes,
                'next_action': next_action,
                'updated_at': datetime.now().isoformat()
            }
            
            # Remove None values
            status_data = {k: v for k, v in status_data.items() if v is not None}
            
            result = self.supabase.table('lead_status').insert(status_data).execute()
            
            if result.data:
                self.logger.info(f"Updated status for lead {lead_id}: {status}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating lead status: {e}")
            return False
    
    async def get_leads_for_outreach(self, limit: int = 50) -> List[Dict]:
        """Get leads that need outreach"""
        try:
            # Get leads that haven't been contacted or need follow-up
            result = self.supabase.table('leads').select('*').gte('ai_lead_score', 40).order('ai_lead_score', desc=True).limit(limit).execute()
            
            if result.data:
                return result.data
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting leads for outreach: {e}")
            return []
    
    async def get_lead_by_id(self, lead_id: int) -> Optional[Dict]:
        """Get a specific lead by ID"""
        try:
            result = self.supabase.table('leads').select('*').eq('id', lead_id).execute()
            
            if result.data:
                return result.data[0]
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting lead {lead_id}: {e}")
            return None
    
    async def create_campaign(self, name: str, storm_location: str, zip_codes: List[str], storm_date: str = None) -> int:
        """Create a new campaign"""
        try:
            campaign_data = {
                'name': name,
                'storm_location': storm_location,
                'storm_date': storm_date,
                'zip_codes': zip_codes,
                'status': 'active'
            }
            
            result = self.supabase.table('campaigns').insert(campaign_data).execute()
            
            if result.data:
                campaign_id = result.data[0]['id']
                self.logger.info(f"Created campaign {campaign_id}: {name}")
                return campaign_id
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating campaign: {e}")
            return None
    
    async def update_campaign_stats(self, campaign_id: int) -> bool:
        """Update campaign statistics"""
        try:
            # Count leads by campaign
            leads_result = self.supabase.table('leads').select('ai_lead_score, ai_qualification_level').eq('campaign_id', campaign_id).execute()
            
            if leads_result.data:
                total_leads = len(leads_result.data)
                qualified_leads = len([l for l in leads_result.data if l.get('ai_lead_score', 0) >= 40])
                
                # Count contacted leads (those with outreach attempts)
                contacted_result = self.supabase.table('outreach_attempts').select('lead_id').execute()
                contacted_lead_ids = set([a['lead_id'] for a in contacted_result.data if contacted_result.data])
                
                campaign_lead_ids = set([l['id'] for l in leads_result.data])
                contacted_leads = len(campaign_lead_ids.intersection(contacted_lead_ids))
                
                # Update campaign
                update_data = {
                    'total_leads': total_leads,
                    'qualified_leads': qualified_leads,
                    'contacted_leads': contacted_leads,
                    'updated_at': datetime.now().isoformat()
                }
                
                result = self.supabase.table('campaigns').update(update_data).eq('id', campaign_id).execute()
                
                return result.data is not None
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating campaign stats: {e}")
            return False
    
    async def get_campaign_dashboard(self, campaign_id: int) -> Dict:
        """Get campaign dashboard data"""
        try:
            # Get campaign info
            campaign_result = self.supabase.table('campaigns').select('*').eq('id', campaign_id).execute()
            
            if not campaign_result.data:
                return {}
            
            campaign = campaign_result.data[0]
            
            # Get lead statistics
            leads_result = self.supabase.table('leads').select('*').eq('campaign_id', campaign_id).execute()
            leads = leads_result.data if leads_result.data else []
            
            # Calculate metrics
            total_leads = len(leads)
            qualified_leads = len([l for l in leads if l.get('ai_lead_score', 0) >= 40])
            hot_leads = len([l for l in leads if l.get('ai_qualification_level') == 'hot'])
            warm_leads = len([l for l in leads if l.get('ai_qualification_level') == 'warm'])
            
            # Get outreach statistics
            outreach_result = self.supabase.table('outreach_attempts').select('*').execute()
            all_outreach = outreach_result.data if outreach_result.data else []
            
            # Filter outreach for this campaign's leads
            campaign_lead_ids = set([l['id'] for l in leads])
            campaign_outreach = [o for o in all_outreach if o['lead_id'] in campaign_lead_ids]
            
            total_outreach = len(campaign_outreach)
            successful_outreach = len([o for o in campaign_outreach if o['status'] in ['sent', 'delivered']])
            
            dashboard = {
                'campaign': campaign,
                'metrics': {
                    'total_leads': total_leads,
                    'qualified_leads': qualified_leads,
                    'hot_leads': hot_leads,
                    'warm_leads': warm_leads,
                    'qualification_rate': (qualified_leads / total_leads * 100) if total_leads > 0 else 0,
                    'total_outreach_attempts': total_outreach,
                    'successful_outreach': successful_outreach,
                    'outreach_success_rate': (successful_outreach / total_outreach * 100) if total_outreach > 0 else 0
                },
                'recent_leads': sorted(leads, key=lambda x: x.get('ai_lead_score', 0), reverse=True)[:10],
                'recent_outreach': sorted(campaign_outreach, key=lambda x: x['attempt_timestamp'], reverse=True)[:10]
            }
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error getting campaign dashboard: {e}")
            return {}
    
    async def search_leads(self, search_term: str, limit: int = 20) -> List[Dict]:
        """Search leads by content, author, or location"""
        try:
            # Search in multiple fields
            results = []
            
            # Search by author
            author_result = self.supabase.table('leads').select('*').ilike('author', f'%{search_term}%').limit(limit).execute()
            if author_result.data:
                results.extend(author_result.data)
            
            # Search by content
            content_result = self.supabase.table('leads').select('*').ilike('content', f'%{search_term}%').limit(limit).execute()
            if content_result.data:
                results.extend(content_result.data)
            
            # Search by location
            location_result = self.supabase.table('leads').select('*').ilike('location', f'%{search_term}%').limit(limit).execute()
            if location_result.data:
                results.extend(location_result.data)
            
            # Remove duplicates
            seen_ids = set()
            unique_results = []
            for lead in results:
                if lead['id'] not in seen_ids:
                    unique_results.append(lead)
                    seen_ids.add(lead['id'])
            
            return unique_results[:limit]
            
        except Exception as e:
            self.logger.error(f"Error searching leads: {e}")
            return []
    
    async def get_outreach_history(self, lead_id: int) -> List[Dict]:
        """Get outreach history for a lead"""
        try:
            result = self.supabase.table('outreach_attempts').select('*').eq('lead_id', lead_id).order('attempt_timestamp', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Error getting outreach history: {e}")
            return []
    
    async def mark_lead_converted(self, lead_id: int, conversion_notes: str = None) -> bool:
        """Mark a lead as converted"""
        try:
            # Update lead status
            await self.update_lead_status(lead_id, 'converted', conversion_notes, 'follow_up_service')
            
            # Update campaign conversion count if applicable
            lead = await self.get_lead_by_id(lead_id)
            if lead and lead.get('campaign_id'):
                campaign_id = lead['campaign_id']
                
                # Get current conversion count
                campaign_result = self.supabase.table('campaigns').select('converted_leads').eq('id', campaign_id).execute()
                
                if campaign_result.data:
                    current_converted = campaign_result.data[0].get('converted_leads', 0)
                    new_converted = current_converted + 1
                    
                    self.supabase.table('campaigns').update({
                        'converted_leads': new_converted,
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', campaign_id).execute()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error marking lead as converted: {e}")
            return False


# Utility functions
async def setup_database():
    """Setup database tables"""
    db = DatabaseManager()
    await db.create_tables()
    return db


async def save_leads_to_db(leads_df: pd.DataFrame, campaign_name: str, storm_location: str) -> Tuple[int, List[int]]:
    """Save leads to database with campaign tracking"""
    db = DatabaseManager()
    
    # Create campaign
    campaign_id = await db.create_campaign(campaign_name, storm_location, [])
    
    # Save leads
    lead_ids = await db.save_leads(leads_df, campaign_id)
    
    # Update campaign stats
    await db.update_campaign_stats(campaign_id)
    
    return campaign_id, lead_ids


if __name__ == "__main__":
    # Test the database manager
    async def main():
        db = DatabaseManager()
        
        # Setup database
        await db.create_tables()
        
        # Create test campaign
        campaign_id = await db.create_campaign(
            "Hurricane Milton - Miami",
            "Miami, FL",
            ["33101", "33102", "33125"]
        )
        
        print(f"Created campaign: {campaign_id}")
        
        # Get dashboard
        dashboard = await db.get_campaign_dashboard(campaign_id)
        print(f"Dashboard: {dashboard}")
    
    asyncio.run(main())