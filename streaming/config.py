import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    
    # Sliding window settings
    FUSION_WINDOW_SECONDS: int = 900  # 15 minutes
    
    # Topic names
    TOPIC_SECURITY: str = "security-telemetry"
    TOPIC_TRANSACTIONS: str = "transaction-events"
    TOPIC_TLS: str = "tls-handshake"
    TOPIC_FUSION_ALERTS: str = "fusion-alerts"
    TOPIC_QUANTUM_ALERTS: str = "quantum-alerts"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
