"""
MergeMind — Application Settings

Loads configuration from environment variables and .env file.
Uses Pydantic Settings for validation and type coercion.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Google Cloud / Gemini ---
    google_api_key: str = ""
    google_cloud_project: str = ""

    # --- GitLab ---
    gitlab_personal_access_token: str = ""
    gitlab_api_url: str = "https://gitlab.com/api/v4"
    gitlab_webhook_secret: str = ""

    # --- MongoDB ---
    mongodb_uri: str = "mongodb://localhost:27017/mergemind"

    # --- Arize AI ---
    arize_space_id: str = ""
    arize_api_key: str = ""

    # Elastic Search
    elastic_id: str | None = None
    elastic_cloud_id: str | None = None
    elastic_api_key: str | None = None

    # --- Fivetran ---
    fivetran_api_key: str = ""
    fivetran_api_secret: str = ""
    fivetran_allow_writes: str = "true"
    
    # --- Dynatrace ---
    dynatrace_environment: str = ""
    dynatrace_api_key: str = ""
    dynatrace_oauth_client_id: str | None = None
    dynatrace_oauth_client_secret: str | None = None

    # --- Business Logic ---
    default_budget_pool: int = 10000
    payment_threshold_score: int = 30
    max_payment_per_mr: int = 500

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


settings = Settings()
