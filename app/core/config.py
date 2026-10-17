from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "CardioBridge ERP Gateway"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./cardio_bridge.db"
    
    # SAP Business One Service Layer
    SAP_SERVICE_LAYER_URL: str = "http://localhost:50000/b1s/v1"
    SAP_COMPANY_DB: str = "SBC_PROD"
    SAP_USERNAME: str = "manager"
    SAP_PASSWORD: str = "password"
    SAP_TIMEOUT_SECONDS: float = 30.0
    SAP_BUSINESS_ONE_TIMEOUT: float = 30.0
    
    # Resiliência & Idempotência
    IDEMPOTENCY_EXPIRE_SECONDS: int = 86400  # 24 horas
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
