import os
from dataclasses import dataclass

@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./nexora.db")
    llm_api_keys: list[str] = None
    model: str = os.getenv("LLM_MODEL", "gemini/gemini-3.8-flash")
    allowed_origins: list[str] = None
    enable_failure_simulation: bool = os.getenv("ENABLE_FAILURE_SIMULATION", "false").lower() == "true"
    default_system_prompt: str = os.getenv("DEFAULT_SYSTEM_PROMPT", "You are Nexora AI, a helpful and accurate assistant.")

    def __post_init__(self):
        self.llm_api_keys = [x.strip() for x in os.getenv("LLM_API_KEYS", "").split(",") if x.strip()]
        self.allowed_origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if x.strip()]

settings = Settings()
