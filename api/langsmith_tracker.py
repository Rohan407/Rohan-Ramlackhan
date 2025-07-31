import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import json
import uuid

from langsmith import Client
from langsmith.schemas import Run, Example
from langsmith.evaluation import evaluate
from config.settings import settings


class LangSmithTracker:
    """LangSmith integration for tracking AI agent performance"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = Client(api_key=settings.langsmith_api_key)
        self.project_name = "roofing-outreach-agent"
        
        # Initialize project
        self._setup_project()
    
    def _setup_project(self):
        """Setup LangSmith project"""
        try:
            # Create project if it doesn't exist
            try:
                self.client.create_project(
                    project_name=self.project_name,
                    description="AI agent for roofing lead qualification and outreach"
                )
                self.logger.info(f"Created LangSmith project: {self.project_name}")
            except Exception:
                # Project likely already exists
                self.logger.info(f"Using existing LangSmith project: {self.project_name}")
                
        except Exception as e:
            self.logger.error(f"Error setting up LangSmith project: {e}")
    
    async def track_lead_qualification(self, lead_data: Dict, qualification_result: Dict, execution_time: float) -> str:
        """Track lead qualification performance"""
        try:
            run_id = str(uuid.uuid4())
            
            # Create run for lead qualification
            run = Run(
                id=run_id,
                name="lead_qualification",
                run_type="chain",
                inputs={
                    "lead_platform": lead_data.get('platform'),
                    "lead_content": lead_data.get('content', '')[:500],  # Truncate for storage
                    "lead_location": lead_data.get('location'),
                    "initial_priority": lead_data.get('potential_lead', {}).get('priority', 'unknown')
                },
                outputs={
                    "ai_lead_score": qualification_result.get('ai_lead_score'),
                    "qualification_level": qualification_result.get('ai_qualification_level'),
                    "urgency_level": qualification_result.get('ai_urgency_level'),
                    "damage_type": qualification_result.get('ai_damage_type'),
                    "project_value": qualification_result.get('ai_project_value')
                },
                start_time=datetime.now(),
                end_time=datetime.now(),
                execution_order=1,
                project_name=self.project_name
            )
            
            # Add custom metadata
            run.extra = {
                "execution_time_seconds": execution_time,
                "lead_author": lead_data.get('author'),
                "search_keyword": lead_data.get('search_keyword'),
                "qualification_notes": qualification_result.get('ai_qualification_notes', '')[:200]
            }
            
            # Submit run to LangSmith
            self.client.create_run(**run.dict())
            
            self.logger.info(f"Tracked lead qualification run: {run_id}")
            return run_id
            
        except Exception as e:
            self.logger.error(f"Error tracking lead qualification: {e}")
            return None
    
    async def track_outreach_attempt(self, lead_data: Dict, outreach_config: Dict, outreach_results: List, execution_time: float) -> str:
        """Track outreach attempt performance"""
        try:
            run_id = str(uuid.uuid4())
            
            # Analyze outreach results
            successful_channels = []
            failed_channels = []
            
            for result in outreach_results:
                if hasattr(result, 'status') and hasattr(result, 'channel'):
                    if result.status.value in ['sent', 'delivered', 'scheduled']:
                        successful_channels.append(result.channel.value)
                    else:
                        failed_channels.append(result.channel.value)
            
            run = Run(
                id=run_id,
                name="outreach_sequence",
                run_type="chain",
                inputs={
                    "lead_score": lead_data.get('ai_lead_score'),
                    "qualification_level": lead_data.get('ai_qualification_level'),
                    "urgency_level": lead_data.get('ai_urgency_level'),
                    "outreach_config": outreach_config,
                    "target_channels": list(outreach_config.keys())
                },
                outputs={
                    "successful_channels": successful_channels,
                    "failed_channels": failed_channels,
                    "total_attempts": len(outreach_results),
                    "success_rate": len(successful_channels) / len(outreach_results) if outreach_results else 0
                },
                start_time=datetime.now(),
                end_time=datetime.now(),
                execution_order=1,
                project_name=self.project_name
            )
            
            # Add metadata
            run.extra = {
                "execution_time_seconds": execution_time,
                "lead_platform": lead_data.get('platform'),
                "lead_location": lead_data.get('location'),
                "damage_type": lead_data.get('ai_damage_type')
            }
            
            self.client.create_run(**run.dict())
            
            self.logger.info(f"Tracked outreach sequence run: {run_id}")
            return run_id
            
        except Exception as e:
            self.logger.error(f"Error tracking outreach attempt: {e}")
            return None
    
    async def track_message_generation(self, lead_data: Dict, message_type: str, generated_message: str, execution_time: float) -> str:
        """Track message generation performance"""
        try:
            run_id = str(uuid.uuid4())
            
            run = Run(
                id=run_id,
                name="message_generation",
                run_type="llm",
                inputs={
                    "message_type": message_type,
                    "lead_content": lead_data.get('content', '')[:300],
                    "lead_location": lead_data.get('location'),
                    "damage_type": lead_data.get('ai_damage_type'),
                    "urgency": lead_data.get('ai_urgency_level')
                },
                outputs={
                    "generated_message": generated_message,
                    "message_length": len(generated_message),
                    "contains_company_name": settings.company_name.lower() in generated_message.lower(),
                    "contains_cta": any(cta in generated_message.lower() for cta in ['call', 'reply', 'contact', 'inspection'])
                },
                start_time=datetime.now(),
                end_time=datetime.now(),
                execution_order=1,
                project_name=self.project_name
            )
            
            run.extra = {
                "execution_time_seconds": execution_time,
                "lead_score": lead_data.get('ai_lead_score'),
                "qualification_level": lead_data.get('ai_qualification_level')
            }
            
            self.client.create_run(**run.dict())
            
            self.logger.info(f"Tracked message generation run: {run_id}")
            return run_id
            
        except Exception as e:
            self.logger.error(f"Error tracking message generation: {e}")
            return None
    
    async def create_evaluation_dataset(self, leads_sample: List[Dict], name: str = "lead_qualification_eval") -> str:
        """Create evaluation dataset for lead qualification"""
        try:
            dataset_name = f"{name}_{datetime.now().strftime('%Y%m%d')}"
            
            examples = []
            for i, lead in enumerate(leads_sample[:50]):  # Limit to 50 examples
                example = Example(
                    inputs={
                        "platform": lead.get('platform'),
                        "content": lead.get('content', ''),
                        "location": lead.get('location'),
                        "author": lead.get('author')
                    },
                    outputs={
                        "expected_score_range": self._determine_expected_score_range(lead),
                        "expected_qualification": self._determine_expected_qualification(lead),
                        "expected_urgency": self._determine_expected_urgency(lead)
                    },
                    metadata={
                        "source": "scraped_data",
                        "created_at": datetime.now().isoformat()
                    }
                )
                examples.append(example)
            
            # Create dataset
            dataset = self.client.create_dataset(
                dataset_name=dataset_name,
                description="Evaluation dataset for lead qualification accuracy"
            )
            
            # Add examples to dataset
            for example in examples:
                self.client.create_example(
                    inputs=example.inputs,
                    outputs=example.outputs,
                    metadata=example.metadata,
                    dataset_id=dataset.id
                )
            
            self.logger.info(f"Created evaluation dataset: {dataset_name} with {len(examples)} examples")
            return dataset.id
            
        except Exception as e:
            self.logger.error(f"Error creating evaluation dataset: {e}")
            return None
    
    def _determine_expected_score_range(self, lead: Dict) -> str:
        """Determine expected score range for evaluation"""
        content = lead.get('content', '').lower()
        
        if any(urgent in content for urgent in ['asap', 'urgent', 'emergency', 'leak']):
            return "80-100"
        elif any(damage in content for damage in ['damage', 'repair', 'fix', 'broken']):
            return "60-90"
        elif any(planning in content for planning in ['planning', 'looking for', 'recommendation']):
            return "40-70"
        else:
            return "20-50"
    
    def _determine_expected_qualification(self, lead: Dict) -> str:
        """Determine expected qualification level for evaluation"""
        content = lead.get('content', '').lower()
        
        if any(urgent in content for urgent in ['asap', 'urgent', 'emergency', 'leak', 'storm damage']):
            return "hot"
        elif any(active in content for active in ['damage', 'repair', 'looking for', 'need']):
            return "warm"
        else:
            return "cold"
    
    def _determine_expected_urgency(self, lead: Dict) -> str:
        """Determine expected urgency level for evaluation"""
        content = lead.get('content', '').lower()
        
        if any(urgent in content for urgent in ['asap', 'urgent', 'emergency', 'immediately']):
            return "urgent"
        elif any(moderate in content for moderate in ['damage', 'repair', 'soon', 'need']):
            return "moderate"
        else:
            return "low"
    
    async def run_evaluation(self, dataset_id: str, qualification_function) -> Dict:
        """Run evaluation on qualification function"""
        try:
            def evaluator(run, example):
                """Custom evaluator for lead qualification"""
                predicted_score = run.outputs.get('ai_lead_score', 0)
                expected_range = example.outputs.get('expected_score_range', '20-50')
                
                # Parse expected range
                range_parts = expected_range.split('-')
                min_expected = int(range_parts[0])
                max_expected = int(range_parts[1])
                
                # Check if predicted score is in expected range
                score_in_range = min_expected <= predicted_score <= max_expected
                
                # Check qualification level
                predicted_qual = run.outputs.get('qualification_level', '').lower()
                expected_qual = example.outputs.get('expected_qualification', '').lower()
                qual_match = predicted_qual == expected_qual
                
                return {
                    "score_in_range": score_in_range,
                    "qualification_match": qual_match,
                    "overall_accuracy": 1.0 if (score_in_range and qual_match) else 0.0
                }
            
            # Run evaluation
            results = evaluate(
                qualification_function,
                data=dataset_id,
                evaluators=[evaluator],
                project_name=f"{self.project_name}_evaluation"
            )
            
            self.logger.info(f"Evaluation completed: {results}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error running evaluation: {e}")
            return {}
    
    async def get_performance_metrics(self, days_back: int = 7) -> Dict:
        """Get performance metrics from LangSmith"""
        try:
            # Get runs from the last N days
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_back)
            
            runs = self.client.list_runs(
                project_name=self.project_name,
                start_time=start_time,
                end_time=end_time
            )
            
            # Analyze runs
            qualification_runs = [r for r in runs if r.name == "lead_qualification"]
            outreach_runs = [r for r in runs if r.name == "outreach_sequence"]
            message_runs = [r for r in runs if r.name == "message_generation"]
            
            metrics = {
                "total_runs": len(runs),
                "qualification_runs": len(qualification_runs),
                "outreach_runs": len(outreach_runs),
                "message_generation_runs": len(message_runs),
                "avg_qualification_time": self._calculate_avg_execution_time(qualification_runs),
                "avg_outreach_time": self._calculate_avg_execution_time(outreach_runs),
                "avg_message_gen_time": self._calculate_avg_execution_time(message_runs),
                "hot_leads_identified": len([r for r in qualification_runs if r.outputs.get('qualification_level') == 'hot']),
                "outreach_success_rate": self._calculate_outreach_success_rate(outreach_runs)
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    def _calculate_avg_execution_time(self, runs: List) -> float:
        """Calculate average execution time for runs"""
        if not runs:
            return 0.0
        
        times = [r.extra.get('execution_time_seconds', 0) for r in runs if r.extra]
        return sum(times) / len(times) if times else 0.0
    
    def _calculate_outreach_success_rate(self, outreach_runs: List) -> float:
        """Calculate overall outreach success rate"""
        if not outreach_runs:
            return 0.0
        
        success_rates = [r.outputs.get('success_rate', 0) for r in outreach_runs if r.outputs]
        return sum(success_rates) / len(success_rates) if success_rates else 0.0
    
    async def track_conversion(self, lead_id: int, conversion_type: str, conversion_value: Optional[float] = None) -> str:
        """Track lead conversion"""
        try:
            run_id = str(uuid.uuid4())
            
            run = Run(
                id=run_id,
                name="lead_conversion",
                run_type="chain",
                inputs={
                    "lead_id": lead_id,
                    "conversion_type": conversion_type
                },
                outputs={
                    "converted": True,
                    "conversion_value": conversion_value,
                    "conversion_date": datetime.now().isoformat()
                },
                start_time=datetime.now(),
                end_time=datetime.now(),
                execution_order=1,
                project_name=self.project_name
            )
            
            run.extra = {
                "conversion_value": conversion_value,
                "conversion_type": conversion_type
            }
            
            self.client.create_run(**run.dict())
            
            self.logger.info(f"Tracked conversion run: {run_id}")
            return run_id
            
        except Exception as e:
            self.logger.error(f"Error tracking conversion: {e}")
            return None


# Utility functions
async def setup_langsmith_tracking() -> LangSmithTracker:
    """Setup LangSmith tracking"""
    tracker = LangSmithTracker()
    return tracker


async def track_full_workflow(leads_df, qualified_leads_df, outreach_results) -> Dict:
    """Track complete workflow performance"""
    tracker = LangSmithTracker()
    
    workflow_metrics = {
        "total_leads_scraped": len(leads_df),
        "total_leads_qualified": len(qualified_leads_df),
        "qualification_rate": len(qualified_leads_df) / len(leads_df) if len(leads_df) > 0 else 0,
        "hot_leads": len(qualified_leads_df[qualified_leads_df['ai_qualification_level'] == 'hot']),
        "warm_leads": len(qualified_leads_df[qualified_leads_df['ai_qualification_level'] == 'warm']),
        "total_outreach_attempts": len(outreach_results),
        "workflow_timestamp": datetime.now().isoformat()
    }
    
    # Track workflow run
    run_id = str(uuid.uuid4())
    
    try:
        run = Run(
            id=run_id,
            name="full_workflow",
            run_type="chain",
            inputs={
                "scraped_leads": len(leads_df),
                "target_platforms": list(set(leads_df['platform'].tolist())) if 'platform' in leads_df.columns else []
            },
            outputs=workflow_metrics,
            start_time=datetime.now(),
            end_time=datetime.now(),
            execution_order=1,
            project_name=tracker.project_name
        )
        
        tracker.client.create_run(**run.dict())
        
    except Exception as e:
        tracker.logger.error(f"Error tracking full workflow: {e}")
    
    return workflow_metrics


if __name__ == "__main__":
    # Test LangSmith tracking
    async def main():
        tracker = LangSmithTracker()
        
        # Sample data for testing
        sample_lead = {
            'platform': 'facebook',
            'content': 'Hurricane damaged my roof, need urgent repair!',
            'location': 'Miami, FL',
            'author': 'John Doe',
            'potential_lead': {'priority': 'high'}
        }
        
        sample_qualification = {
            'ai_lead_score': 85,
            'ai_qualification_level': 'hot',
            'ai_urgency_level': 'urgent',
            'ai_damage_type': 'storm damage',
            'ai_project_value': '$15,000-$25,000'
        }
        
        # Track qualification
        run_id = await tracker.track_lead_qualification(sample_lead, sample_qualification, 2.5)
        print(f"Tracked qualification: {run_id}")
        
        # Get metrics
        metrics = await tracker.get_performance_metrics(7)
        print(f"Performance metrics: {metrics}")
    
    asyncio.run(main())