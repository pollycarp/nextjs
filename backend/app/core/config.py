from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "research-assistant")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")

    # CORS: origins allowed to talk to the backend
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    REQUIRED_KEYS: list[str] = ["GOOGLE_API_KEY"]

    def validate(self) -> list[str]:
        """Return a list of missing required environment variables."""
        missing = []
        for key in self.REQUIRED_KEYS:
            if not getattr(self, key):
                missing.append(key)
        return missing


settings = Settings()
