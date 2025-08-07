# YouTube to Plex

Automatically download videos from YouTube channels and organize them for Plex with proper episode detection and metadata.

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get YouTube API key**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable YouTube Data API v3
   - Create credentials (API key)

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your API key
   ```

4. **Configure channels and settings**
   ```bash
   # Edit config.yaml with your YouTube channel and preferences
   ```

## Usage

```bash
python src/main_downloader.py
```

Videos are downloaded to `~/tv-shows` with Plex-compatible naming and metadata.

## Features

- Automatic episode detection from video titles
- Plex-compatible file organization
- Duplicate detection (skips already downloaded videos)
- Subtitle downloads
- NFO metadata files for Plex
- Configurable quality and filters