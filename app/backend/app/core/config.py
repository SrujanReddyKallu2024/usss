from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LLM_BASE_URL: str = "https://router.huggingface.co/v1"
    LLM_API_KEY: str = ""
    LLM_CHAT_MODEL: str = "Qwen/Qwen2.5-Coder-32B-Instruct"

    EMBED_MODEL: str = "BAAI/bge-small-en-v1.5"

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/real_estate"
    DATABASE_URL_READONLY: str = "postgresql+psycopg://chatbot_ro:readonly@localhost:5432/real_estate"

    model_config = SettingsConfigDict(
        env_file=("../../../.env", "../../.env", "../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
