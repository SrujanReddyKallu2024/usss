# Application settings, loaded from the project .env file.
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM (OpenAI SDK pointed at any compatible router)
    LLM_BASE_URL: str = "https://router.huggingface.co/v1"
    LLM_API_KEY: str = ""
    LLM_CHAT_MODEL: str = "Qwen/Qwen2.5-Coder-32B-Instruct"

    # Embeddings (run locally with fastembed)
    EMBED_MODEL: str = "BAAI/bge-small-en-v1.5"

    # Databases
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/real_estate"
    DATABASE_URL_READONLY: str = "postgresql+psycopg://chatbot_ro:readonly@localhost:5432/real_estate"

    # Read the .env that sits one level above the app folder.
    model_config = SettingsConfigDict(
        env_file=("../.env", "../../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# One shared settings object for the whole app.
settings = Settings()
