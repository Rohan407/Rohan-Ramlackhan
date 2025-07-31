import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings and configuration"""
    
    # API Keys
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    twilio_account_sid: str = Field(..., env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(..., env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str = Field(..., env="TWILIO_PHONE_NUMBER")
    elevenlabs_api_key: str = Field(..., env="ELEVENLABS_API_KEY")
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    langsmith_api_key: str = Field(..., env="LANGSMITH_API_KEY")
    google_credentials_path: str = Field(..., env="GOOGLE_CREDENTIALS_PATH")
    
    # Social Media Credentials (optional)
    facebook_email: Optional[str] = Field(None, env="FACEBOOK_EMAIL")
    facebook_password: Optional[str] = Field(None, env="FACEBOOK_PASSWORD")
    
    # Application Settings
    app_name: str = "RoofingOutreachAgent"
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # Business Settings
    company_name: str = Field("Premium Roofing Solutions", env="COMPANY_NAME")
    business_phone: str = Field(..., env="BUSINESS_PHONE")
    service_area_radius: int = Field(50, env="SERVICE_AREA_RADIUS")  # miles
    
    # Outreach Settings
    max_daily_calls: int = Field(100, env="MAX_DAILY_CALLS")
    max_daily_sms: int = Field(200, env="MAX_DAILY_SMS")
    call_hours_start: int = Field(9, env="CALL_HOURS_START")  # 9 AM
    call_hours_end: int = Field(18, env="CALL_HOURS_END")    # 6 PM
    
    # Database Settings
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()