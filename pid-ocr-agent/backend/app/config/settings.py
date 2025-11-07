"""
Application Settings and Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """

    # Application
    APP_NAME: str = "P&ID OCR Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/pidocr"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1 hour

    # MinIO Object Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_DOCUMENTS: str = "pid-documents"
    MINIO_BUCKET_EXPORTS: str = "pid-exports"

    # OCR Configuration
    TESSERACT_PATH: Optional[str] = "/usr/bin/tesseract"
    OCR_LANGUAGE: str = "eng"
    OCR_DPI: int = 300
    OCR_PAGE_SEGMENTATION_MODE: int = 3  # Fully automatic page segmentation
    OCR_ENGINE_MODE: int = 3  # Default (Legacy + LSTM)

    # Image Processing
    IMAGE_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    IMAGE_SUPPORTED_FORMATS: List[str] = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"]
    IMAGE_PREPROCESSING_ENABLED: bool = True
    IMAGE_RESIZE_MAX_DIMENSION: int = 4000

    # AI Model Configuration
    MODEL_PATH: str = "/app/models"
    SYMBOL_RECOGNITION_MODEL: str = "pid_symbol_classifier_v1"
    CONFIDENCE_THRESHOLD: float = 0.75
    BATCH_SIZE: int = 32

    # HAZOP Configuration
    HAZOP_GUIDE_WORDS: List[str] = [
        "NO/NONE", "MORE", "LESS", "AS WELL AS",
        "PART OF", "REVERSE", "OTHER THAN"
    ]
    HAZOP_PARAMETERS: List[str] = [
        "FLOW", "PRESSURE", "TEMPERATURE", "LEVEL",
        "COMPOSITION", "PH", "VISCOSITY"
    ]
    HAZOP_RISK_MATRIX: dict = {
        "severity": ["Negligible", "Minor", "Moderate", "Major", "Catastrophic"],
        "likelihood": ["Rare", "Unlikely", "Possible", "Likely", "Almost Certain"]
    }

    # Instrument Index Configuration
    ISA_TAG_PREFIXES: List[str] = [
        "FE", "FT", "FC", "FI", "FY", "FV", "FIC", "FRC",
        "PT", "PI", "PC", "PY", "PCV", "PSV", "PSHH", "PSL",
        "TT", "TI", "TC", "TE", "TY", "TCV",
        "LT", "LI", "LC", "LE", "LY", "LAH", "LAL", "LAHH", "LALL",
        "AT", "AE", "AI", "AC",
        "CV", "HV", "MOV", "SOV",
        "HS", "ZS", "FS"
    ]

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # File Processing
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    TEMP_UPLOAD_DIR: str = "/tmp/pid-uploads"
    PROCESSING_TIMEOUT: int = 600  # 10 minutes
    MAX_CONCURRENT_JOBS: int = 5

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None

    # Export Configuration
    EXPORT_PDF_DPI: int = 300
    EXPORT_MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    EXPORT_RETENTION_DAYS: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    """
    return Settings()


# Export settings instance
settings = get_settings()
