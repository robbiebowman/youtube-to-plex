# YouTube to Plex

Automatically download videos from YouTube channels and organize them for Plex with proper episode detection and metadata.

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get YouTube API key**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable [YouTube Data API v3](https://console.cloud.google.com/marketplace/product/google/youtube.googleapis.com)
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
# Basic usage (uses config.yaml settings)
python src/main_downloader.py

# Override channel and time window
python src/main_downloader.py --channel "https://www.youtube.com/@SomeChannel" --days 30

# Dry run to see what would be downloaded
python src/main_downloader.py --dry-run

# Download from specific channel for last 7 days
python src/main_downloader.py --channel "@CosmicPumpkin" --days 7
```

### Command Line Options

- `--channel URL` - Override the YouTube channel URL from config
- `--days N` - Override the number of days to look back for videos
- `--dry-run` - Show what would be downloaded without actually downloading
- `--max-videos N` - Maximum number of videos to check (default: 50)
- `--status` - Show current downloader status
- `--force-download URL` - Force download a specific video URL

Videos are downloaded to `~/tv-shows` with Plex-compatible naming and metadata.

## Features

- **Smart episode detection** - Handles multiple formats:
  - `Series S01E05` / `series s03e05` 
  - `Series Season 12 Episode 4`
  - `Series 1x01` 
  - `Only Connect - Series 21 - Episode 3`
  - `University Challenge Series 54 Episode 37`
  - Falls back to channel name for unmatched titles
- **Plex-compatible file organization** - `/Series Name/Season 01/Series - S01E05 - Title.mp4`
- **Duplicate detection** - Skips already downloaded videos
- **Subtitle downloads** - Automatic subtitle fetching
- **NFO metadata files** - Full Plex metadata support
- **Configurable quality and filters** - Control what gets downloaded