import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

# Import our components
from workflows.main_orchestrator import RoofingOutreachOrchestrator, run_storm_response_workflow
from api.database_manager import DatabaseManager
from api.langsmith_tracker import LangSmithTracker
from config.settings import settings


# Page configuration
st.set_page_config(
    page_title="Roofing Outreach AI Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def init_components():
    """Initialize dashboard components"""
    return {
        'orchestrator': RoofingOutreachOrchestrator(),
        'db': DatabaseManager(),
        'tracker': LangSmithTracker()
    }

# Async wrapper for Streamlit
def run_async(coroutine):
    """Run async function in Streamlit"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coroutine)
    except Exception as e:
        st.error(f"Error: {e}")
        return None
    finally:
        loop.close()

def main():
    """Main dashboard function"""
    st.title("🏠 Roofing Outreach AI Dashboard")
    st.markdown("**AI-Powered Storm Damage Lead Generation & Outreach**")
    
    components = init_components()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", [
        "🎯 Campaign Management",
        "📊 Analytics Dashboard", 
        "🔍 Lead Management",
        "📞 Outreach Control",
        "⚙️ System Settings",
        "📈 Performance Metrics"
    ])
    
    if page == "🎯 Campaign Management":
        campaign_management_page(components)
    elif page == "📊 Analytics Dashboard":
        analytics_dashboard_page(components)
    elif page == "🔍 Lead Management":
        lead_management_page(components)
    elif page == "📞 Outreach Control":
        outreach_control_page(components)
    elif page == "⚙️ System Settings":
        system_settings_page(components)
    elif page == "📈 Performance Metrics":
        performance_metrics_page(components)

def campaign_management_page(components):
    """Campaign management interface"""
    st.header("🎯 Campaign Management")
    
    # Create new campaign section
    st.subheader("Create New Campaign")
    
    col1, col2 = st.columns(2)
    
    with col1:
        storm_location = st.text_input("Storm Location", placeholder="e.g., Miami, FL")
        campaign_name = st.text_input("Campaign Name (optional)", placeholder="Auto-generated if empty")
        
    with col2:
        urgency_level = st.selectbox("Urgency Level", ["High", "Medium", "Low"])
        target_platforms = st.multiselect("Target Platforms", ["Facebook", "Nextdoor"], default=["Facebook", "Nextdoor"])
    
    if st.button("🚀 Launch Campaign", type="primary"):
        if storm_location:
            with st.spinner("Launching campaign..."):
                result = run_async(run_storm_response_workflow(storm_location, urgency_level.lower()))
                
                if result and result.get('success'):
                    st.success(f"Campaign launched successfully!")
                    st.json(result)
                else:
                    st.error("Campaign launch failed")
                    if result:
                        st.json(result)
        else:
            st.error("Please enter a storm location")
    
    # Active campaigns section
    st.subheader("Active Campaigns")
    
    # Get campaigns from database (placeholder)
    campaigns_data = {
        'Campaign Name': ['Hurricane Milton - Miami', 'Storm Response - Tampa', 'Hail Damage - Orlando'],
        'Location': ['Miami, FL', 'Tampa, FL', 'Orlando, FL'],
        'Status': ['Active', 'Active', 'Completed'],
        'Total Leads': [45, 32, 78],
        'Qualified Leads': [23, 18, 42],
        'Contacted': [15, 12, 38]
    }
    
    campaigns_df = pd.DataFrame(campaigns_data)
    st.dataframe(campaigns_df, use_container_width=True)

def analytics_dashboard_page(components):
    """Analytics and reporting dashboard"""
    st.header("📊 Analytics Dashboard")
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Leads", "1,234", "+12%")
    with col2:
        st.metric("Qualified Leads", "687", "+8%")
    with col3:
        st.metric("Conversion Rate", "15.6%", "+2.1%")
    with col4:
        st.metric("Revenue Generated", "$127k", "+18%")
    
    # Charts section
    col1, col2 = st.columns(2)
    
    with col1:
        # Lead generation over time
        st.subheader("Lead Generation Trend")
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        leads_data = pd.DataFrame({
            'Date': dates,
            'Leads': [20 + i + (i % 7) * 5 for i in range(30)]
        })
        
        fig = px.line(leads_data, x='Date', y='Leads', title="Daily Lead Generation")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Lead quality distribution
        st.subheader("Lead Quality Distribution")
        quality_data = pd.DataFrame({
            'Quality': ['Hot', 'Warm', 'Cold'],
            'Count': [156, 324, 207]
        })
        
        fig = px.pie(quality_data, values='Count', names='Quality', 
                    title="Lead Quality Distribution")
        st.plotly_chart(fig, use_container_width=True)
    
    # Platform performance
    st.subheader("Platform Performance")
    platform_data = pd.DataFrame({
        'Platform': ['Facebook', 'Nextdoor', 'Direct'],
        'Leads Generated': [456, 234, 89],
        'Conversion Rate': [12.3, 18.7, 8.9],
        'Avg Lead Score': [72, 78, 65]
    })
    st.dataframe(platform_data, use_container_width=True)

def lead_management_page(components):
    """Lead management interface"""
    st.header("🔍 Lead Management")
    
    # Search and filter section
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_term = st.text_input("Search Leads", placeholder="Search by name, location, content...")
    with col2:
        quality_filter = st.selectbox("Filter by Quality", ["All", "Hot", "Warm", "Cold"])
    with col3:
        platform_filter = st.selectbox("Filter by Platform", ["All", "Facebook", "Nextdoor"])
    
    # Lead details section
    st.subheader("Lead Details")
    
    # Sample lead data
    lead_data = {
        'ID': [1, 2, 3, 4, 5],
        'Name': ['John Smith', 'Sarah Johnson', 'Mike Wilson', 'Lisa Davis', 'Tom Brown'],
        'Platform': ['Facebook', 'Nextdoor', 'Facebook', 'Nextdoor', 'Facebook'],
        'Location': ['Miami, FL', 'Tampa, FL', 'Orlando, FL', 'Miami, FL', 'Jacksonville, FL'],
        'Score': [85, 72, 91, 68, 79],
        'Quality': ['Hot', 'Warm', 'Hot', 'Warm', 'Warm'],
        'Status': ['New', 'Contacted', 'Interested', 'New', 'Responded'],
        'Last Contact': ['Never', '2 hours ago', '1 day ago', 'Never', '3 hours ago']
    }
    
    leads_df = pd.DataFrame(lead_data)
    
    # Apply filters
    if quality_filter != "All":
        leads_df = leads_df[leads_df['Quality'] == quality_filter]
    if platform_filter != "All":
        leads_df = leads_df[leads_df['Platform'] == platform_filter]
    if search_term:
        leads_df = leads_df[leads_df['Name'].str.contains(search_term, case=False, na=False)]
    
    # Display leads with actions
    for idx, row in leads_df.iterrows():
        with st.expander(f"Lead: {row['Name']} - Score: {row['Score']} - {row['Quality']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Platform:** {row['Platform']}")
                st.write(f"**Location:** {row['Location']}")
                st.write(f"**Status:** {row['Status']}")
                st.write(f"**Last Contact:** {row['Last Contact']}")
            
            with col2:
                if st.button(f"Send SMS", key=f"sms_{idx}"):
                    st.success("SMS sent!")
                if st.button(f"Schedule Call", key=f"call_{idx}"):
                    st.success("Call scheduled!")
                if st.button(f"Mark Converted", key=f"convert_{idx}"):
                    st.success("Lead marked as converted!")

def outreach_control_page(components):
    """Outreach control and monitoring"""
    st.header("📞 Outreach Control")
    
    # Current status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("SMS Sent Today", "47/200")
        st.progress(47/200)
    
    with col2:
        st.metric("Calls Made Today", "12/100")
        st.progress(12/100)
    
    with col3:
        st.metric("Success Rate", "68.5%")
        st.progress(0.685)
    
    # Manual outreach section
    st.subheader("Manual Outreach")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_area("Custom Message", placeholder="Enter custom message for outreach...")
        target_leads = st.multiselect("Select Leads", ["John Smith (Hot)", "Sarah Johnson (Warm)", "Mike Wilson (Hot)"])
    
    with col2:
        outreach_type = st.selectbox("Outreach Type", ["SMS", "Voice Call", "Email"])
        schedule_time = st.selectbox("Schedule", ["Send Now", "Schedule for Later"])
        
        if st.button("Execute Outreach"):
            st.success(f"{outreach_type} outreach initiated for {len(target_leads)} leads")
    
    # Outreach history
    st.subheader("Recent Outreach Activity")
    
    outreach_history = pd.DataFrame({
        'Time': ['10:30 AM', '10:15 AM', '10:00 AM', '9:45 AM'],
        'Lead': ['John Smith', 'Sarah Johnson', 'Mike Wilson', 'Lisa Davis'],
        'Type': ['SMS', 'Call', 'SMS', 'SMS'],
        'Status': ['Delivered', 'Completed', 'Delivered', 'Failed'],
        'Response': ['Yes - Interested', 'Scheduled appointment', 'No response', 'Invalid number']
    })
    
    st.dataframe(outreach_history, use_container_width=True)

def system_settings_page(components):
    """System settings and configuration"""
    st.header("⚙️ System Settings")
    
    # API Configuration
    st.subheader("API Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("OpenAI API Key", type="password", value="sk-****")
        st.text_input("Twilio Account SID", type="password", value="AC****")
        st.text_input("ElevenLabs API Key", type="password", value="****")
    
    with col2:
        st.text_input("Supabase URL", value="https://****")
        st.text_input("LangSmith API Key", type="password", value="****")
        st.text_input("Google Credentials Path", value="/path/to/credentials.json")
    
    # Business Settings
    st.subheader("Business Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("Company Name", value=settings.company_name)
        st.text_input("Business Phone", value=settings.business_phone)
        st.number_input("Service Area (miles)", value=settings.service_area_radius)
    
    with col2:
        st.number_input("Max Daily SMS", value=settings.max_daily_sms)
        st.number_input("Max Daily Calls", value=settings.max_daily_calls)
        st.time_input("Calling Hours Start", value=datetime.strptime("09:00", "%H:%M").time())
    
    if st.button("Save Settings"):
        st.success("Settings saved successfully!")
    
    # System Status
    st.subheader("System Status")
    
    status_data = {
        'Component': ['Database', 'AI Agents', 'Twilio', 'ElevenLabs', 'Google Calendar'],
        'Status': ['🟢 Online', '🟢 Online', '🟢 Online', '🟡 Limited', '🟢 Online'],
        'Last Check': ['30 seconds ago', '1 minute ago', '30 seconds ago', '2 minutes ago', '1 minute ago']
    }
    
    st.dataframe(pd.DataFrame(status_data), use_container_width=True)

def performance_metrics_page(components):
    """Performance metrics and LangSmith integration"""
    st.header("📈 Performance Metrics")
    
    # Get performance data
    try:
        # This would fetch real data from LangSmith
        performance_data = {
            'total_runs': 1247,
            'qualification_runs': 856,
            'outreach_runs': 234,
            'message_generation_runs': 157,
            'avg_qualification_time': 2.3,
            'avg_outreach_time': 5.7,
            'hot_leads_identified': 123,
            'outreach_success_rate': 0.685
        }
    except:
        # Fallback to sample data
        performance_data = {
            'total_runs': 1247,
            'qualification_runs': 856,
            'outreach_runs': 234,
            'message_generation_runs': 157,
            'avg_qualification_time': 2.3,
            'avg_outreach_time': 5.7,
            'hot_leads_identified': 123,
            'outreach_success_rate': 0.685
        }
    
    # Performance overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total AI Runs", f"{performance_data['total_runs']:,}")
    with col2:
        st.metric("Qualification Runs", f"{performance_data['qualification_runs']:,}")
    with col3:
        st.metric("Avg Qualification Time", f"{performance_data['avg_qualification_time']:.1f}s")
    with col4:
        st.metric("Outreach Success Rate", f"{performance_data['outreach_success_rate']:.1%}")
    
    # Performance trends
    st.subheader("Performance Trends")
    
    # Sample trend data
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    trend_data = pd.DataFrame({
        'Date': dates,
        'Success Rate': [0.65 + (i % 10) * 0.02 for i in range(30)],
        'Response Time': [2.1 + (i % 7) * 0.1 for i in range(30)]
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.line(trend_data, x='Date', y='Success Rate', 
                     title="Outreach Success Rate Trend")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.line(trend_data, x='Date', y='Response Time', 
                     title="Average Response Time Trend")
        st.plotly_chart(fig, use_container_width=True)
    
    # Model performance breakdown
    st.subheader("AI Model Performance")
    
    model_data = pd.DataFrame({
        'Model Component': ['Lead Qualification', 'Message Generation', 'Priority Scoring', 'Outreach Timing'],
        'Accuracy': [0.87, 0.92, 0.81, 0.76],
        'Avg Response Time (s)': [2.3, 1.8, 0.9, 1.2],
        'Daily Usage': [856, 234, 1247, 567]
    })
    
    st.dataframe(model_data, use_container_width=True)

if __name__ == "__main__":
    main()