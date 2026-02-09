from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class SSHSettings(BaseSettings):
    host: str = Field("localhost", alias="SSH_HOST")
    user: str = Field("user", alias="SSH_USER")
    key_path: str = Field("id_rsa", alias="SSH_KEY_PATH")
    remote_port: int = Field(8188, alias="SSH_REMOTE_PORT")
    local_port: int = Field(8189, alias="SSH_LOCAL_PORT")

class AppSettings(BaseSettings):
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    
    # SSH Settings
    ssh_host: Optional[str] = Field(None, alias="SSH_HOST")
    ssh_user: Optional[str] = Field(None, alias="SSH_USER")
    ssh_key_path: Optional[str] = Field(None, alias="SSH_KEY_PATH")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
