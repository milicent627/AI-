from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    data_dir: str = str(Path(__file__).parent.parent.parent / "data")
    model_config = {"env_prefix": "BW_", "extra": "allow"}


settings = Settings()
