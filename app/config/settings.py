import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    Central configuration manager using pydantic-settings.
    Loads variables from environment or a .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=('settings_',)
    )

    # API Keys & LLM settings
    google_api_key: str = Field(
        default="",
        validation_alias="GOOGLE_API_KEY"
    )
    model_name: str = Field(
        default="gemini-1.5-flash",
        validation_alias="MODEL_NAME"
    )
    temperature: float = Field(
        default=0.0,
        validation_alias="TEMPERATURE"
    )

    # Retrieval settings
    top_k: int = Field(
        default=5,
        validation_alias="TOP_K"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        validation_alias="EMBEDDING_MODEL"
    )

    # Path configurations (relative to workspace root)
    base_dir: str = Field(default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    raw_data_dir: str = Field(default="data/raw")
    processed_data_dir: str = Field(default="data/processed")
    index_dir: str = Field(default="data/index")
    prompts_dir: str = Field(default="app/prompts")

    @property
    def raw_catalog_path(self) -> str:
        return os.path.join(self.base_dir, self.raw_data_dir, "raw_catalog.json")

    @property
    def processed_catalog_path(self) -> str:
        return os.path.join(self.base_dir, self.processed_data_dir, "catalog.json")

    @property
    def faiss_index_path(self) -> str:
        return os.path.join(self.base_dir, self.index_dir, "faiss_index.bin")

    @property
    def bm25_index_path(self) -> str:
        return os.path.join(self.base_dir, self.index_dir, "bm25_index.pkl")

    @property
    def metadata_path(self) -> str:
        return os.path.join(self.base_dir, self.index_dir, "metadata.pkl")

# Initialize global settings
settings = Settings()
