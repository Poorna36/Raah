"""
RAAH Backend Configuration
Centralized configuration management for backend services
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Backend configuration settings"""
    
    # Application settings
    APP_NAME: str = "RAAH Backend Core"
    VERSION: str = "2.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/raah",
        env="DATABASE_URL"
    )
    
    # Redis settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        env="REDIS_URL"
    )
    
    # JWT settings
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        env="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Security settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="ALLOWED_ORIGINS"
    )
    API_KEY_HEADER: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    
    # Stream settings
    REDIS_STREAM_NAMES: List[str] = Field(
        default=["stream:anpr", "stream:fastag", "stream:cctv"],
        env="REDIS_STREAM_NAMES"
    )
    STREAM_CONSUMER_GROUP: str = Field(default="raah_backend", env="STREAM_CONSUMER_GROUP")
    STREAM_CONSUMER_NAME: str = Field(default="backend_1", env="STREAM_CONSUMER_NAME")
    STREAM_BLOCK_TIMEOUT_MS: int = Field(default=5000, env="STREAM_BLOCK_TIMEOUT_MS")
    
    # Processing settings
    BATCH_SIZE: int = Field(default=100, env="BATCH_SIZE")
    PROCESSING_INTERVAL_SECONDS: int = Field(default=1, env="PROCESSING_INTERVAL_SECONDS")
    JOURNEY_TIMEOUT_MINUTES: int = Field(default=60, env="JOURNEY_TIMEOUT_MINUTES")
    
    # Alert settings
    ALERT_COOLDOWN_MINUTES: int = Field(default=5, env="ALERT_COOLDOWN_MINUTES")
    MAX_ALERTS_PER_MINUTE: int = Field(default=10, env="MAX_ALERTS_PER_MINUTE")
    ALERT_RETENTION_DAYS: int = Field(default=30, env="ALERT_RETENTION_DAYS")
    
    # Zone settings
    ZONE_UPDATE_INTERVAL_SECONDS: int = Field(default=30, env="ZONE_UPDATE_INTERVAL_SECONDS")
    BASELINE_CALCULATION_DAYS: int = Field(default=7, env="BASELINE_CALCULATION_DAYS")
    ANOMALY_THRESHOLD_ZSCORE: float = Field(default=2.0, env="ANOMALY_THRESHOLD_ZSCORE")
    
    # Hard logic settings
    E1_NO_FASTAG_THRESHOLD: int = Field(default=1, env="E1_NO_FASTAG_THRESHOLD")
    E2_UNDERPAYMENT_THRESHOLD: int = Field(default=1, env="E2_UNDERPAYMENT_THRESHOLD")
    E3_CLASS_MISMATCH_THRESHOLD: int = Field(default=1, env="E3_CLASS_MISMATCH_THRESHOLD")
    E4_UNREGISTERED_THRESHOLD: int = Field(default=1, env="E4_UNREGISTERED_THRESHOLD")
    E5_SPEED_THRESHOLD_KMH: int = Field(default=120, env="E5_SPEED_THRESHOLD_KMH")
    
    # ML settings
    ML_SERVICE_URL: str = Field(default="http://localhost:8002", env="ML_SERVICE_URL")
    ML_TIMEOUT_SECONDS: int = Field(default=5, env="ML_TIMEOUT_SECONDS")
    ML_RETRY_ATTEMPTS: int = Field(default=3, env="ML_RETRY_ATTEMPTS")
    
    # Simulator settings
    SIMULATOR_URL: str = Field(default="http://localhost:8001", env="SIMULATOR_URL")
    SIMULATOR_TIMEOUT_SECONDS: int = Field(default=5, env="SIMULATOR_TIMEOUT_SECONDS")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    RATE_LIMIT_BURST_SIZE: int = Field(default=10, env="RATE_LIMIT_BURST_SIZE")
    
    # File upload settings
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, env="MAX_UPLOAD_SIZE_MB")
    UPLOAD_ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".pdf"],
        env="UPLOAD_ALLOWED_EXTENSIONS"
    )
    
    # WebSocket settings
    WEBSOCKET_PING_INTERVAL: int = Field(default=30, env="WEBSOCKET_PING_INTERVAL")
    WEBSOCKET_PING_TIMEOUT: int = Field(default=10, env="WEBSOCKET_PING_TIMEOUT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Derived settings
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 40
DATABASE_POOL_TIMEOUT = 30

# Redis settings
REDIS_KEY_PREFIX = "raah:"
REDIS_JOURNEY_PREFIX = f"{REDIS_KEY_PREFIX}journey:"
REDIS_ZONE_PREFIX = f"{REDIS_KEY_PREFIX}zone:"
REDIS_ALERT_PREFIX = f"{REDIS_KEY_PREFIX}alert:"
REDIS_SESSION_PREFIX = f"{REDIS_KEY_PREFIX}session:"

# Cache TTL settings
CACHE_TTL_SHORT = 60  # 1 minute
CACHE_TTL_MEDIUM = 300  # 5 minutes
CACHE_TTL_LONG = 3600  # 1 hour

# Alert severity levels
ALERT_SEVERITY_INFO = "info"
ALERT_SEVERITY_WARNING = "warning"
ALERT_SEVERITY_CRITICAL = "critical"
ALERT_SEVERITY_EMERGENCY = "emergency"

# Event types
EVENT_TYPE_ANPR = "anpr"
EVENT_TYPE_FASTAG = "fastag"
EVENT_TYPE_CCTV = "cctv"

# Journey statuses
JOURNEY_STATUS_ACTIVE = "active"
JOURNEY_STATUS_COMPLETED = "completed"
JOURNEY_STATUS_EXPIRED = "expired"
JOURNEY_STATUS_ANOMALOUS = "anomalous"

# Zone types
ZONE_TYPE_HIGHWAY = "highway"
ZONE_TYPE_TOLL_PLAZA = "toll_plaza"
ZONE_TYPE_FOREST_CORRIDOR = "forest_corridor"

# Vehicle classes
VEHICLE_CLASS_CAR = "Car"
VEHICLE_CLASS_LMV = "LMV"
VEHICLE_CLASS_BUS = "Bus"
VEHICLE_CLASS_TRUCK = "Truck"
VEHICLE_CLASS_MAV = "MAV"
VEHICLE_CLASS_2W = "2W"

# Hard logic evasion types
EVASION_TYPE_E1_NO_FASTAG = "E1_NO_FASTAG"
EVASION_TYPE_E2_UNDERPAYMENT = "E2_UNDERPAYMENT"
EVASION_TYPE_E3_CLASS_MISMATCH = "E3_CLASS_MISMATCH"
EVASION_TYPE_E4_UNREGISTERED = "E4_UNREGISTERED"
EVASION_TYPE_E5_SPEEDING = "E5_SPEEDING"

# Alert categories
ALERT_CATEGORY_EVASION = "evasion"
ALERT_CATEGORY_ANOMALY = "anomaly"
ALERT_CATEGORY_INCIDENT = "incident"
ALERT_CATEGORY_WILDLIFE = "wildlife"
ALERT_CATEGORY_SYSTEM = "system"

# Response codes
RESPONSE_CODE_SUCCESS = "SUCCESS"
RESPONSE_CODE_ERROR = "ERROR"
RESPONSE_CODE_VALIDATION_ERROR = "VALIDATION_ERROR"
RESPONSE_CODE_NOT_FOUND = "NOT_FOUND"
RESPONSE_CODE_UNAUTHORIZED = "UNAUTHORIZED"
RESPONSE_CODE_FORBIDDEN = "FORBIDDEN"
RESPONSE_CODE_RATE_LIMITED = "RATE_LIMITED"

# Default pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

def get_database_url() -> str:
    """Get database URL with connection pooling parameters"""
    base_url = settings.DATABASE_URL
    if "?" not in base_url:
        return f"{base_url}?pool_size={DATABASE_POOL_SIZE}&max_overflow={DATABASE_MAX_OVERFLOW}"
    return base_url

def get_redis_url() -> str:
    """Get Redis URL"""
    return settings.REDIS_URL

def is_production() -> bool:
    """Check if running in production"""
    return settings.DEBUG is False and "localhost" not in settings.HOST

def get_allowed_origins() -> List[str]:
    """Get allowed CORS origins"""
    return settings.ALLOWED_ORIGINS

def get_jwt_config() -> dict:
    """Get JWT configuration"""
    return {
        "secret_key": settings.JWT_SECRET_KEY,
        "algorithm": settings.JWT_ALGORITHM,
        "access_token_expire_minutes": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        "refresh_token_expire_days": settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    }