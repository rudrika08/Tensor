import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Tensor Credit Intelligence API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://tensor:tensor123@localhost:5432/tensordb"
    )

    # Storage
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")  # local | s3 | gcs
    LOCAL_UPLOAD_DIR: str = os.getenv("LOCAL_UPLOAD_DIR", "uploads")
    AWS_BUCKET_NAME: str = os.getenv("AWS_BUCKET_NAME", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    # Google Maps
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

    # Vision Models
    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", "models/yolov8m.pt")
    SAM_CHECKPOINT_PATH: str = os.getenv("SAM_CHECKPOINT_PATH", "models/sam_vit_h.pth")
    SAM_MODEL_TYPE: str = os.getenv("SAM_MODEL_TYPE", "vit_h")
    MIDAS_MODEL_TYPE: str = os.getenv("MIDAS_MODEL_TYPE", "DPT_Large")
    CLIP_MODEL_NAME: str = os.getenv("CLIP_MODEL_NAME", "ViT-B-32")
    CLIP_PRETRAINED: str = os.getenv("CLIP_PRETRAINED", "openai")

    # Validation thresholds
    MIN_IMAGE_WIDTH: int = 640
    MIN_IMAGE_HEIGHT: int = 480
    BLUR_THRESHOLD: float = 100.0
    MAX_IMAGES_PER_SUBMISSION: int = 5
    MIN_IMAGES_PER_SUBMISSION: int = 3
    MAX_IMAGE_SIZE_MB: int = 20
    MAX_TEMPORAL_GAP_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000", "*"]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
