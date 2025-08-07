# YouTube to Plex Downloader - Technical Design

## Overview
A Python-based scheduled script that monitors a YouTube channel, identifies videos matching specific criteria, downloads them, and stores them in a local directory for Plex media server consumption.

## Architecture Components

### 1. Configuration Management
- **Config File**: `config.yaml` - stores all parameterized settings
- **Environment Variables**: Optional overrides for sensitive data (API keys)
- **Default Parameters**: Sensible defaults for all configurable options

### 2. YouTube Channel Monitoring
- **Approach**: YouTube Data API v3 (primary) with fallback to RSS feed parsing
- **Channel Discovery**: Support for channel URL, channel ID, or handle (@username)
- **Video Metadata**: Extract title, upload date, description, duration, view count

### 3. Video Filtering System
- **Upload Recency**: Configurable time window (e.g., last 7 days)
- **Title Matching**: Fuzzy string matching using `fuzzywuzzy` library
- **Additional Filters**: Duration limits, view count thresholds, keyword exclusions

### 4. Download Management
- **Tool**: `yt-dlp` (actively maintained fork of youtube-dl)
- **Quality Selection**: Configurable video quality preferences
- **Naming Convention**: Plex-friendly naming with episode detection
- **Storage**: Organized directory structure in `~/tv-shows`

### 5. Scheduling System
- **Primary**: Cron job for Unix-like systems
- **Alternative**: Python `schedule` library for cross-platform support
- **Logging**: Comprehensive logging for monitoring and debugging

## Implementation Steps

### Phase 1: Core Infrastructure
1. **Project Setup**
   - Create Python virtual environment
   - Install dependencies: `yt-dlp`, `PyYAML`, `fuzzywuzzy`, `google-api-python-client`, `schedule`
   - Set up project directory structure

2. **Configuration System**
   - Design `config.yaml` schema
   - Implement configuration loader with validation
   - Add environment variable support for API keys

3. **Logging Framework**
   - Configure Python logging with rotation
   - Add structured logging for monitoring
   - Create log directory and retention policy

### Phase 2: YouTube Integration
4. **YouTube API Client**
   - Implement YouTube Data API v3 wrapper
   - Add RSS feed fallback for quota management
   - Handle rate limiting and error scenarios

5. **Channel Monitoring**
   - Fetch recent videos from target channel
   - Parse video metadata and thumbnails
   - Cache results to avoid redundant API calls

### Phase 3: Video Processing
6. **Filtering Engine**
   - Implement upload date filtering
   - Add fuzzy title matching with configurable threshold
   - Create extensible filter plugin system

7. **Download Manager**
   - Configure yt-dlp with optimal settings
   - Implement download progress tracking
   - Add file verification and cleanup

### Phase 4: Storage and Organization
8. **File Management**
   - Create Plex-compatible directory structure
   - Implement intelligent episode numbering
   - Add metadata file generation (NFO files)

9. **Duplicate Prevention**
   - Track downloaded videos in SQLite database
   - Implement checksum-based duplicate detection
   - Add manual override capabilities

### Phase 5: Scheduling and Monitoring
10. **Scheduler Implementation**
    - Create cron job installer script
    - Add systemd timer support (Linux)
    - Implement standalone scheduler mode

11. **Monitoring and Logging**
    - Implement health check endpoints
    - Create dashboard for status monitoring

## Configuration Schema

```yaml
youtube:
  api_key: "${YOUTUBE_API_KEY}"  # Environment variable
  channel_url: "https://www.youtube.com/@channelname"
  quota_limit: 10000  # Daily API quota limit

filters:
  upload_window_days: 7  # Only check videos from last N days
  title_patterns:
    - pattern: "episode"
      fuzzy_threshold: 80  # 0-100 similarity score
    - pattern: "season finale"
      fuzzy_threshold: 90
  min_duration_minutes: 10
  max_duration_minutes: 120
  exclude_keywords:
    - "trailer"
    - "preview"
    - "behind the scenes"

download:
  quality: "best[height<=1080]"  # yt-dlp format selector
  output_path: "~/tv-shows/%(uploader)s/Season %(season)s/%(title)s.%(ext)s"
  audio_only: false
  subtitle_languages: ["en", "en-US"]

storage:
  base_directory: "~/tv-shows"
  organize_by_season: true
  generate_metadata: true  # Create .nfo files for Plex
  cleanup_partial_downloads: true

schedule:
  enabled: true
  cron_expression: "0 18 * * 1"  # 6 PM every Monday
  timezone: "America/New_York"

# No notifications configured - using logs only

logging:
  level: "INFO"
  file_path: "logs/youtube-downloader.log"
  max_file_size_mb: 10
  backup_count: 5
```

## Security Considerations
- Store API keys in environment variables
- Implement rate limiting to respect YouTube's terms of service
- Add input validation for all configuration parameters
- Use secure file permissions for logs and downloads

## Error Handling
- Graceful degradation when YouTube API is unavailable
- Retry logic with exponential backoff
- Comprehensive error logging
- Recovery mechanisms for interrupted downloads

## Testing Strategy
- Unit tests for filtering logic
- Integration tests with YouTube API
- Mock testing for download scenarios
- End-to-end testing with test channels

## Deployment Options
1. **Local Cron Job**: Traditional Unix cron scheduling
2. **Systemd Timer**: Modern Linux scheduling with better logging
3. **Docker Container**: Containerized deployment with volume mounts
4. **Cloud Function**: Serverless execution with cloud storage

## Future Enhancements
- Web UI for configuration and monitoring
- Multiple channel support
- Plex library refresh automation
- Advanced episode detection and numbering
- Integration with other media managers (Sonarr, Radarr)