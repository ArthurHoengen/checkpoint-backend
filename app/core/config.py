from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    ollama_base_url: str

    class Config:
        env_file = ".env"

settings = Settings()