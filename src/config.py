import os
import yaml
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv


class TitlePattern(BaseModel):
    pattern: str
    fuzzy_threshold: int = Field(ge=0, le=100)


class YouTubeConfig(BaseModel):
    api_key: str
    channel_url: str
    quota_limit: int = Field(default=10000, ge=1)
    
    @validator('channel_url')
    def validate_channel_url(cls, v):
        youtube_patterns = [
            r'https?://(?:www\.)?youtube\.com/@[\w-]+',
            r'https?://(?:www\.)?youtube\.com/channel/[\w-]+',
            r'https?://(?:www\.)?youtube\.com/c/[\w-]+',
            r'https?://(?:www\.)?youtube\.com/user/[\w-]+'
        ]
        if not any(re.match(pattern, v) for pattern in youtube_patterns):
            raise ValueError('Invalid YouTube channel URL format')
        return v


class FiltersConfig(BaseModel):
    upload_window_days: int = Field(default=7, ge=1)
    title_patterns: List[TitlePattern] = Field(default_factory=list)
    min_duration_minutes: Optional[int] = Field(default=None, ge=0)
    max_duration_minutes: Optional[int] = Field(default=None, ge=1)
    exclude_keywords: List[str] = Field(default_factory=list)
    
    @validator('max_duration_minutes')
    def validate_duration_range(cls, v, values):
        if v is not None and 'min_duration_minutes' in values:
            min_dur = values['min_duration_minutes']
            if min_dur is not None and v <= min_dur:
                raise ValueError('max_duration_minutes must be greater than min_duration_minutes')
        return v


class DownloadConfig(BaseModel):
    quality: str = "best[height<=1080]"
    output_path: str = "~/tv-shows/%(uploader)s/Season %(season)s/%(title)s.%(ext)s"
    audio_only: bool = False
    subtitle_languages: List[str] = Field(default_factory=lambda: ["en", "en-US"])


class StorageConfig(BaseModel):
    base_directory: str = "~/tv-shows"
    organize_by_season: bool = True
    generate_metadata: bool = True
    cleanup_partial_downloads: bool = True
    
    @validator('base_directory')
    def validate_base_directory(cls, v):
        expanded_path = Path(v).expanduser()
        if not expanded_path.parent.exists():
            raise ValueError(f'Parent directory of {expanded_path} does not exist')
        return str(expanded_path)


class ScheduleConfig(BaseModel):
    enabled: bool = True
    cron_expression: str = "0 18 * * 1"
    timezone: str = "America/New_York"
    
    @validator('cron_expression')
    def validate_cron(cls, v):
        parts = v.split()
        if len(parts) != 5:
            raise ValueError('Cron expression must have exactly 5 parts')
        return v


# Email notifications removed - using logs only


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    file_path: str = "logs/youtube-downloader.log"
    max_file_size_mb: int = Field(default=10, ge=1)
    backup_count: int = Field(default=5, ge=0)


class Config(BaseModel):
    youtube: YouTubeConfig
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    download: DownloadConfig = Field(default_factory=DownloadConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
# notifications removed - using logs only
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def expand_env_variables(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively expand environment variables in configuration data."""
    if isinstance(data, dict):
        return {key: expand_env_variables(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [expand_env_variables(item) for item in data]
    elif isinstance(data, str):
        # Expand environment variables like ${VAR_NAME}
        pattern = re.compile(r'\$\{([^}]+)\}')
        
        def replace_env_var(match):
            env_var = match.group(1)
            return os.getenv(env_var, match.group(0))  # Return original if not found
        
        return pattern.sub(replace_env_var, data)
    else:
        return data


def load_config(config_path: str = "config.yaml", env_path: str = ".env") -> Config:
    """Load and validate configuration from YAML file and environment variables."""
    # Load environment variables
    if os.path.exists(env_path):
        load_dotenv(env_path)
    
    # Load YAML configuration
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as file:
        config_data = yaml.safe_load(file)
    
    # Expand environment variables
    config_data = expand_env_variables(config_data)
    
    # Validate and create config object
    try:
        config = Config(**config_data)
        return config
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


def validate_config_file(config_path: str = "config.yaml", env_path: str = ".env") -> bool:
    """Validate configuration file without loading it into memory."""
    try:
        config = load_config(config_path, env_path)
        print("✓ Configuration file is valid")
        
        # Check if required environment variables are set
        missing_vars = []
        if not config.youtube.api_key or "${YOUTUBE_API_KEY}" in config.youtube.api_key:
            missing_vars.append("YOUTUBE_API_KEY")
        
# Email notifications removed - no additional environment variables needed
        
        if missing_vars:
            print(f"⚠ Missing environment variables: {', '.join(missing_vars)}")
            print("  Create .env file with these variables (see .env.example)")
            return False
        
        print("✓ All required environment variables are set")
        return True
        
    except Exception as e:
        print(f"✗ Configuration validation failed: {e}")
        return False