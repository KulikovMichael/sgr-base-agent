from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    litellm_api_key: str = Field(..., description='API ключ доступа к LiteLLM')
    model_name: str = Field('gpt-4o-mini', description='Имя используемой LLM модели')
    litellm_base_url: str | None = Field(
        default=None,
        description='Базовый URL прокси/шлюза LiteLLM. Если не задан, используется публичный API.',
    )


settings = Settings()
