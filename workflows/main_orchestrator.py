import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path

import pandas as pd
import schedule
import time
import threading

# Import our custom modules
from scrapers.facebook_scraper import scrape_facebook_leads
from scrapers.nextdoor_scraper import scrape_nextdoor_leads, get_storm_affected_zip_codes
from agents.lead_qualification_agent import qualify_scraped_leads
from agents.outreach_agent import execute_priority_outreach
from api.database_manager import DatabaseManager, save_leads_to_db
from api.langsmith_tracker import LangSmithTracker, track_full_workflow
from config.settings import settings


class RoofingOutreachOrchestrator:
    """Main orchestrator for the roofing outreach AI system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager()
        self.tracker = LangSmithTracker()
        self.is_running = False
        self.current_campaign_id = None
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        asyncio.create_task(self._initialize_components())
    
    def _setup_logging(self):
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=getattr(logging, settings.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/orchestrator.log'),
                logging.StreamHandler()
            ]
        )
    
    async def _initialize_components(self):
        """Initialize database and other components"""
        try:
            await self.db.create_tables()
            self.logger.info("Orchestrator initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing orchestrator: {e}")
    
    async def run_full_workflow(self, storm_location: str, campaign_name: str = None) -> Dict:
        """Run the complete lead generation and outreach workflow"""
        workflow_start = datetime.now()
        
        try:
            if not campaign_name:
                campaign_name = f"Storm Outreach - {storm_location} - {datetime.now().strftime('%Y-%m-%d')}"
            
            self.logger.info(f"Starting full workflow for {storm_location}")
            
            # Step 1: Get affected zip codes
            zip_codes = get_storm_affected_zip_codes(storm_location)
            self.logger.info(f"Targeting {len(zip_codes)} zip codes: {zip_codes}")
            
            # Step 2: Create campaign
            campaign_id = await self.db.create_campaign(
                name=campaign_name,
                storm_location=storm_location,
                zip_codes=zip_codes,
                storm_date=datetime.now().strftime('%Y-%m-%d')
            )
            self.current_campaign_id = campaign_id
            
            # Step 3: Scrape social media platforms
            self.logger.info("Starting social media scraping...")
            scraping_results = await self._scrape_all_platforms(storm_location, zip_codes)
            
            if scraping_results['total_leads'] == 0:
                self.logger.warning("No leads found during scraping")
                return self._create_workflow_summary(workflow_start, scraping_results, None, None)
            
            # Step 4: Qualify leads with AI
            self.logger.info(f"Qualifying {scraping_results['total_leads']} leads...")
            qualified_leads_df = await qualify_scraped_leads(scraping_results['all_leads_df'])
            
            # Step 5: Save to database
            lead_ids = await self.db.save_leads(qualified_leads_df, campaign_id)
            await self.db.update_campaign_stats(campaign_id)
            
            # Step 6: Create priority outreach queue
            from agents.lead_qualification_agent import get_priority_outreach_queue
            priority_queue = await get_priority_outreach_queue(qualified_leads_df)
            
            # Step 7: Execute outreach
            self.logger.info(f"Executing outreach for {len(priority_queue)} priority leads...")
            outreach_results = await execute_priority_outreach(priority_queue)
            
            # Step 8: Track performance
            await self._track_workflow_performance(
                scraping_results['all_leads_df'],
                qualified_leads_df,
                outreach_results
            )
            
            # Step 9: Generate workflow summary
            workflow_summary = self._create_workflow_summary(
                workflow_start,
                scraping_results,
                qualified_leads_df,
                outreach_results
            )
            
            self.logger.info(f"Workflow completed successfully: {workflow_summary}")
            return workflow_summary
            
        except Exception as e:
            self.logger.error(f"Error in full workflow: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _scrape_all_platforms(self, storm_location: str, zip_codes: List[str]) -> Dict:
        """Scrape all social media platforms"""
        all_leads = []
        platform_results = {}
        
        try:
            # Scrape Facebook
            self.logger.info("Scraping Facebook...")
            facebook_leads = await scrape_facebook_leads(storm_location, days_back=30)
            platform_results['facebook'] = {
                'leads_found': len(facebook_leads),
                'status': 'success' if len(facebook_leads) > 0 else 'no_results'
            }
            
            if len(facebook_leads) > 0:
                all_leads.append(facebook_leads)
            
            # Scrape Nextdoor
            self.logger.info("Scraping Nextdoor...")
            nextdoor_leads = await scrape_nextdoor_leads(zip_codes, storm_location)
            platform_results['nextdoor'] = {
                'leads_found': len(nextdoor_leads),
                'status': 'success' if len(nextdoor_leads) > 0 else 'no_results'
            }
            
            if len(nextdoor_leads) > 0:
                all_leads.append(nextdoor_leads)
            
            # Combine all leads
            if all_leads:
                combined_df = pd.concat(all_leads, ignore_index=True)
                # Remove duplicates based on content
                combined_df = combined_df.drop_duplicates(subset=['content'], keep='first')
            else:
                combined_df = pd.DataFrame()
            
            return {
                'platform_results': platform_results,
                'total_leads': len(combined_df),
                'all_leads_df': combined_df
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping platforms: {e}")
            return {
                'platform_results': platform_results,
                'total_leads': 0,
                'all_leads_df': pd.DataFrame(),
                'error': str(e)
            }
    
    async def _track_workflow_performance(self, scraped_df: pd.DataFrame, qualified_df: pd.DataFrame, outreach_results: List):
        """Track workflow performance in LangSmith"""
        try:
            await track_full_workflow(scraped_df, qualified_df, outreach_results)
        except Exception as e:
            self.logger.error(f"Error tracking workflow performance: {e}")
    
    def _create_workflow_summary(self, start_time: datetime, scraping_results: Dict, 
                                qualified_leads_df: Optional[pd.DataFrame], outreach_results: Optional[List]) -> Dict:
        """Create comprehensive workflow summary"""
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        summary = {
            'success': True,
            'execution_time_seconds': execution_time,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'campaign_id': self.current_campaign_id,
            'scraping': scraping_results
        }
        
        if qualified_leads_df is not None:
            # Lead qualification metrics
            total_qualified = len(qualified_leads_df)
            hot_leads = len(qualified_leads_df[qualified_leads_df['ai_qualification_level'] == 'hot'])
            warm_leads = len(qualified_leads_df[qualified_leads_df['ai_qualification_level'] == 'warm'])
            cold_leads = len(qualified_leads_df[qualified_leads_df['ai_qualification_level'] == 'cold'])
            
            summary['qualification'] = {
                'total_qualified': total_qualified,
                'hot_leads': hot_leads,
                'warm_leads': warm_leads,
                'cold_leads': cold_leads,
                'avg_lead_score': float(qualified_leads_df['ai_lead_score'].mean()) if total_qualified > 0 else 0,
                'qualification_rate': total_qualified / scraping_results['total_leads'] if scraping_results['total_leads'] > 0 else 0
            }
        
        if outreach_results:
            # Outreach metrics
            total_outreach = len(outreach_results)
            successful_outreach = sum(1 for result in outreach_results 
                                    if any(attempt.status.value in ['sent', 'delivered'] 
                                          for attempt in result.get('outreach_results', [])))
            
            summary['outreach'] = {
                'total_leads_contacted': total_outreach,
                'successful_contacts': successful_outreach,
                'contact_success_rate': successful_outreach / total_outreach if total_outreach > 0 else 0
            }
        
        return summary
    
    async def run_scheduled_workflow(self, storm_location: str, schedule_time: str = "09:00"):
        """Schedule recurring workflow execution"""
        def job():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.run_full_workflow(storm_location))
            finally:
                loop.close()
        
        schedule.every().day.at(schedule_time).do(job)
        
        self.logger.info(f"Scheduled daily workflow for {storm_location} at {schedule_time}")
        
        # Run scheduler in background thread
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)
        
        self.is_running = True
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
    
    async def run_monitoring_workflow(self):
        """Run continuous monitoring of leads and outreach"""
        while self.is_running:
            try:
                # Check for leads needing follow-up
                await self._check_follow_up_leads()
                
                # Monitor outreach performance
                await self._monitor_outreach_performance()
                
                # Update campaign statistics
                if self.current_campaign_id:
                    await self.db.update_campaign_stats(self.current_campaign_id)
                
                # Wait before next check
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in monitoring workflow: {e}")
                await asyncio.sleep(60)
    
    async def _check_follow_up_leads(self):
        """Check for leads that need follow-up"""
        try:
            # Get leads that haven't been contacted recently
            leads = await self.db.get_leads_for_outreach(limit=20)
            
            for lead in leads:
                # Check last outreach attempt
                outreach_history = await self.db.get_outreach_history(lead['id'])
                
                if not outreach_history:
                    # Lead has never been contacted
                    self.logger.info(f"Lead {lead['id']} needs initial outreach")
                elif len(outreach_history) > 0:
                    last_attempt = outreach_history[0]
                    last_attempt_time = datetime.fromisoformat(last_attempt['attempt_timestamp'])
                    
                    # Check if follow-up is needed (24+ hours since last attempt)
                    if (datetime.now() - last_attempt_time).total_seconds() > 86400:
                        self.logger.info(f"Lead {lead['id']} needs follow-up outreach")
        
        except Exception as e:
            self.logger.error(f"Error checking follow-up leads: {e}")
    
    async def _monitor_outreach_performance(self):
        """Monitor real-time outreach performance"""
        try:
            # Get performance metrics from LangSmith
            metrics = await self.tracker.get_performance_metrics(days_back=1)
            
            # Log key metrics
            if metrics:
                self.logger.info(f"Daily performance: {metrics.get('total_runs', 0)} total runs, "
                               f"{metrics.get('outreach_success_rate', 0):.1%} outreach success rate")
        
        except Exception as e:
            self.logger.error(f"Error monitoring performance: {e}")
    
    async def process_inbound_response(self, from_number: str, message_body: str, platform: str = 'sms') -> str:
        """Process inbound responses from leads"""
        try:
            self.logger.info(f"Processing inbound response from {from_number}: {message_body}")
            
            # Find the lead in database
            # In production, you'd have better phone number matching
            leads = await self.db.search_leads(from_number, limit=1)
            
            if leads:
                lead = leads[0]
                lead_id = lead['id']
                
                # Update lead status based on response
                if any(word in message_body.lower() for word in ['yes', 'interested', 'call']):
                    await self.db.update_lead_status(lead_id, 'interested', f"Positive response: {message_body}")
                    response = f"Great! A {settings.company_name} specialist will call you soon. For urgent needs: {settings.business_phone}"
                
                elif any(word in message_body.lower() for word in ['no', 'stop', 'unsubscribe']):
                    await self.db.update_lead_status(lead_id, 'opted_out', f"Opted out: {message_body}")
                    response = "Understood. We've removed you from our list."
                
                else:
                    await self.db.update_lead_status(lead_id, 'responded', f"General response: {message_body}")
                    response = f"Thanks for your message! A {settings.company_name} representative will respond shortly."
                
                return response
            
            else:
                # Unknown number
                return f"Thanks for contacting {settings.company_name}! Please call {settings.business_phone} for assistance."
        
        except Exception as e:
            self.logger.error(f"Error processing inbound response: {e}")
            return f"Thanks for your message! Please call {settings.business_phone} for assistance."
    
    async def get_campaign_dashboard(self, campaign_id: Optional[int] = None) -> Dict:
        """Get comprehensive campaign dashboard"""
        try:
            if not campaign_id:
                campaign_id = self.current_campaign_id
            
            if not campaign_id:
                return {'error': 'No active campaign'}
            
            dashboard = await self.db.get_campaign_dashboard(campaign_id)
            
            # Add real-time performance metrics
            performance_metrics = await self.tracker.get_performance_metrics(days_back=7)
            dashboard['performance_metrics'] = performance_metrics
            
            return dashboard
        
        except Exception as e:
            self.logger.error(f"Error getting campaign dashboard: {e}")
            return {'error': str(e)}
    
    async def emergency_stop(self):
        """Emergency stop for all operations"""
        self.logger.warning("Emergency stop initiated")
        self.is_running = False
        
        # Cancel any running tasks
        # In production, you'd have better task management
        
    def stop(self):
        """Gracefully stop the orchestrator"""
        self.logger.info("Stopping orchestrator...")
        self.is_running = False


# Utility functions for different workflow types
async def run_storm_response_workflow(storm_location: str, urgency: str = "high") -> Dict:
    """Quick storm response workflow"""
    orchestrator = RoofingOutreachOrchestrator()
    
    campaign_name = f"Emergency Storm Response - {storm_location} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    return await orchestrator.run_full_workflow(storm_location, campaign_name)


async def run_maintenance_workflow(target_locations: List[str]) -> Dict:
    """Regular maintenance and follow-up workflow"""
    orchestrator = RoofingOutreachOrchestrator()
    
    results = {}
    for location in target_locations:
        campaign_name = f"Maintenance Outreach - {location} - {datetime.now().strftime('%Y-%m-%d')}"
        result = await orchestrator.run_full_workflow(location, campaign_name)
        results[location] = result
    
    return results


async def setup_continuous_monitoring(storm_locations: List[str]) -> RoofingOutreachOrchestrator:
    """Setup continuous monitoring for multiple locations"""
    orchestrator = RoofingOutreachOrchestrator()
    
    # Schedule workflows for each location
    for location in storm_locations:
        await orchestrator.run_scheduled_workflow(location, "09:00")
    
    # Start monitoring
    asyncio.create_task(orchestrator.run_monitoring_workflow())
    
    return orchestrator


if __name__ == "__main__":
    # Example usage
    async def main():
        # Test full workflow
        result = await run_storm_response_workflow("Miami, FL")
        print(f"Workflow result: {json.dumps(result, indent=2)}")
        
        # Setup continuous monitoring
        # orchestrator = await setup_continuous_monitoring(["Miami, FL", "Houston, TX"])
        # Keep running...
        # await asyncio.sleep(3600)  # Run for 1 hour
    
    asyncio.run(main())