import json
import os
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime

import yt_dlp

from config import Config
from logging_config import LoggerMixin, log_performance
from youtube_client import YouTubeVideo


class DownloadProgress:
    """Tracks download progress for a video."""
    
    def __init__(self, video_id: str, title: str):
        self.video_id = video_id
        self.title = title
        self.status = "pending"  # pending, downloading, completed, failed
        self.progress_percent = 0.0
        self.speed = ""
        self.eta = ""
        self.file_size = ""
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.error_message = ""
        self.output_path = ""
        self.start_time = None
        self.end_time = None


# Database caching removed - using file existence checking instead


class PlexNamingHelper:
    """Helper for Plex-compatible file naming and organization."""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        # Remove/replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'[^\w\s\-_\.\(\)]', '', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200] + "..."
        
        return filename
    
    @staticmethod
    def extract_episode_info(title: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
        """Extract series name, season, and episode from title."""
        # Common patterns for episode identification (order matters!)
        patterns = [
            # "Series S01E05" or "Series S1E5" - must come first
            r'(.+?)\s+S(\d+)E(\d+)',
            # "Series Season 1 Episode 5"
            r'(.+?)\s+Season\s+(\d+)\s+Episode\s+(\d+)',
            # "Series 1x05"
            r'(.+?)\s+(\d+)x(\d+)',
            # "Series Series 21 Episode 3" or "Program Series 54 Episode 37"
            r'(.+?)\s+Series\s+(\d+)\s+Episode\s+(\d+)',
            # "Series - Series 15 - Episode 2"
            r'(.+?)\s+-\s+Series\s+(\d+)\s+-\s+Episode\s+(\d+)',
            # "Series - Episode 5" (assume Season 1)
            r'(.+?)\s+-\s+Episode\s+(\d+)',
            # "Series Episode 5" (assume Season 1)
            r'(.+?)\s+Episode\s+(\d+)',
            # Look for numbers at the end
            r'(.+?)\s+(\d+)$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                if len(match.groups()) == 3:
                    series_name = match.group(1).strip()
                    season = int(match.group(2))
                    episode = int(match.group(3))
                    return series_name, season, episode
                elif len(match.groups()) == 2:
                    series_name = match.group(1).strip()
                    season = 1  # Default to season 1
                    episode = int(match.group(2))
                    return series_name, season, episode
        
        # If no pattern matches, return None for series (will trigger fallback)
        return None, None, None
    
    @staticmethod
    def generate_plex_path(video: YouTubeVideo, base_dir: str, organize_by_season: bool = True) -> Tuple[str, str]:
        """Generate Plex-compatible file path and filename."""
        base_path = Path(base_dir).expanduser()
        
        # Extract episode information
        series_name, season, episode = PlexNamingHelper.extract_episode_info(video.title)
        
        # Fallback to channel name if no series detected
        if series_name is None:
            series_name = video.channel_title or "Unknown Channel"
            season = None
            episode = None
        
        # Sanitize series name for directory
        series_dir = PlexNamingHelper.sanitize_filename(series_name)
        
        # Create directory structure
        if organize_by_season and season is not None and episode is not None:
            # Plex format: /Series Name/Season 01/
            season_dir = f"Season {season:02d}"
            full_dir = base_path / series_dir / season_dir
            
            # Plex filename format: Series Name - S01E05 - Episode Title.ext
            filename = f"{series_dir} - S{season:02d}E{episode:02d} - {PlexNamingHelper.sanitize_filename(video.title)}"
        else:
            # Simple organization: /Series Name/ or /Channel Name/
            full_dir = base_path / series_dir
            filename = PlexNamingHelper.sanitize_filename(video.title)
        
        return str(full_dir), filename


class DownloadManager(LoggerMixin):
    """Manages video downloads using yt-dlp with Plex organization."""
    
    def __init__(self, config: Config):
        self.config = config
        self.current_downloads: Dict[str, DownloadProgress] = {}
        
        # Create base download directory
        self.base_dir = Path(config.storage.base_directory).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def is_already_downloaded(self, video: YouTubeVideo) -> bool:
        """Check if video file already exists."""
        output_dir, filename_base = PlexNamingHelper.generate_plex_path(
            video, 
            str(self.base_dir),
            self.config.storage.organize_by_season
        )
        
        output_path = Path(output_dir)
        if not output_path.exists():
            return False
        
        # Look for any video file with our base name
        for ext in ['.mp4', '.mkv', '.webm', '.m4a', '.mp3', '.flv']:
            potential_file = output_path / f"{filename_base}{ext}"
            if potential_file.exists() and potential_file.stat().st_size > 0:
                self.logger.debug(f"Found existing file: {potential_file}")
                return True
        
        return False
    
    def _progress_hook(self, video_id: str) -> Callable:
        """Create a progress hook for yt-dlp."""
        def hook(d):
            if video_id not in self.current_downloads:
                return
            
            progress = self.current_downloads[video_id]
            
            if d['status'] == 'downloading':
                progress.status = 'downloading'
                progress.downloaded_bytes = d.get('downloaded_bytes', 0) or 0
                progress.total_bytes = d.get('total_bytes', 0) or 0
                
                if progress.total_bytes and progress.total_bytes > 0:
                    progress.progress_percent = (progress.downloaded_bytes / progress.total_bytes) * 100
                
                progress.speed = d.get('_speed_str', '')
                progress.eta = d.get('_eta_str', '')
                progress.file_size = d.get('_total_bytes_str', '')
                
                # Log progress periodically
                if int(progress.progress_percent) % 10 == 0:
                    self.logger.info(f"Download progress for {video_id}: {progress.progress_percent:.1f}%")
            
            elif d['status'] == 'finished':
                progress.status = 'completed'
                progress.progress_percent = 100.0
                progress.output_path = d.get('filename', '')
                progress.end_time = datetime.now()
                self.logger.info(f"Download completed: {d.get('filename', 'Unknown')}")
            
            elif d['status'] == 'error':
                progress.status = 'failed'
                progress.error_message = str(d.get('error', 'Unknown error'))
                progress.end_time = datetime.now()
                self.logger.error(f"Download failed for {video_id}: {progress.error_message}")
        
        return hook
    
# Checksum calculation removed - using file existence for duplicate detection
    
    def _create_nfo_file(self, video: YouTubeVideo, video_path: str):
        """Create NFO metadata file for Plex."""
        if not self.config.storage.generate_metadata:
            return
        
        nfo_path = Path(video_path).with_suffix('.nfo')
        
        # Basic NFO content for Plex
        nfo_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<episodedetails>
    <title>{video.title}</title>
    <plot>{video.description[:500]}...</plot>
    <aired>{video.published_datetime.strftime('%Y-%m-%d')}</aired>
    <studio>YouTube</studio>
    <tag>YouTube</tag>
    <uniqueid type="youtube">{video.video_id}</uniqueid>
    <runtime>{video.duration_minutes or 0}</runtime>
</episodedetails>"""
        
        try:
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(nfo_content)
            self.logger.debug(f"Created NFO file: {nfo_path}")
        except Exception as e:
            self.logger.error(f"Error creating NFO file {nfo_path}: {e}")
    
    @log_performance
    def download_video(self, video: YouTubeVideo, progress_callback: Optional[Callable] = None) -> bool:
        """Download a single video with progress tracking."""
        # Check if already downloaded
        if self.is_already_downloaded(video):
            self.logger.info(f"Video '{video.title}' already exists, skipping download")
            return True
        
        # Create progress tracker
        progress = DownloadProgress(video.video_id, video.title)
        progress.start_time = datetime.now()
        self.current_downloads[video.video_id] = progress
        
        try:
            # Generate Plex-compatible path
            output_dir, filename_base = PlexNamingHelper.generate_plex_path(
                video, 
                str(self.base_dir),
                self.config.storage.organize_by_season
            )
            
            # Create output directory
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': self.config.download.quality,
                'outtmpl': os.path.join(output_dir, f"{filename_base}.%(ext)s"),
                'progress_hooks': [self._progress_hook(video.video_id)],
                'writesubtitles': bool(self.config.download.subtitle_languages),
                'writeautomaticsub': True,
                'subtitleslangs': self.config.download.subtitle_languages,
                'ignoreerrors': False,
                'no_warnings': False
            }
            
            # Audio-only option
            if self.config.download.audio_only:
                ydl_opts['format'] = 'bestaudio/best'
            
            self.logger.info(f"Starting download: {video.title}")
            self.logger.debug(f"Download options: {ydl_opts}")
            
            # Download with yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video.url])
            
            # Find the downloaded file
            downloaded_file = None
            output_path = Path(output_dir)
            
            # Look for any file starting with our filename base
            for file_path in output_path.glob(f"{filename_base}.*"):
                if file_path.suffix in ['.mp4', '.mkv', '.webm', '.m4a', '.mp3', '.flv']:
                    downloaded_file = file_path
                    break
            
            # If still not found, look for any video file in the directory
            if not downloaded_file:
                for ext in ['.mp4', '.mkv', '.webm', '.m4a', '.mp3', '.flv']:
                    for file_path in output_path.glob(f"*{ext}"):
                        if file_path.name.startswith(filename_base[:20]):  # Partial match
                            downloaded_file = file_path
                            break
                    if downloaded_file:
                        break
            
            if not downloaded_file:
                raise Exception("Downloaded file not found")
            
            # Calculate file size
            file_size = downloaded_file.stat().st_size
            
            # Create NFO metadata file
            self._create_nfo_file(video, str(downloaded_file))
            
            # Update progress
            progress.status = 'completed'
            progress.output_path = str(downloaded_file)
            progress.end_time = datetime.now()
            
            self.logger.info(f"Successfully downloaded: {downloaded_file} ({file_size / (1024*1024):.1f} MB)")
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(progress)
            
            return True
            
        except Exception as e:
            progress.status = 'failed'
            progress.error_message = str(e)
            progress.end_time = datetime.now()
            
            self.logger.error(f"Download failed for {video.video_id}: {e}")
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(progress)
            
            return False
            
        finally:
            # Clean up current downloads tracker
            if video.video_id in self.current_downloads:
                del self.current_downloads[video.video_id]
    
    def download_videos(self, videos: List[YouTubeVideo], progress_callback: Optional[Callable] = None) -> Dict[str, bool]:
        """Download multiple videos and return results."""
        results = {}
        
        self.logger.info(f"Starting batch download of {len(videos)} videos")
        
        for i, video in enumerate(videos, 1):
            self.logger.info(f"Downloading {i}/{len(videos)}: {video.title}")
            
            try:
                success = self.download_video(video, progress_callback)
                results[video.video_id] = success
                
                if success:
                    self.logger.info(f"✅ Downloaded: {video.title}")
                else:
                    self.logger.error(f"❌ Failed: {video.title}")
                    
            except Exception as e:
                self.logger.error(f"❌ Error downloading {video.title}: {e}")
                results[video.video_id] = False
        
        # Summary
        successful = sum(1 for success in results.values() if success)
        self.logger.info(f"Batch download complete: {successful}/{len(videos)} successful")
        
        return results
    
    def cleanup_partial_downloads(self):
        """Clean up any partial or failed downloads."""
        if not self.config.storage.cleanup_partial_downloads:
            return
        
        self.logger.info("Cleaning up partial downloads...")
        
        # Look for .part files and other temporary files
        cleanup_patterns = ['*.part', '*.tmp', '*.ytdl']
        cleaned_count = 0
        
        for pattern in cleanup_patterns:
            for file_path in self.base_dir.rglob(pattern):
                try:
                    file_path.unlink()
                    cleaned_count += 1
                    self.logger.debug(f"Cleaned up: {file_path}")
                except Exception as e:
                    self.logger.error(f"Error cleaning up {file_path}: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} partial download files")
    
    def get_download_status(self) -> Dict:
        """Get current download status and statistics."""
        # Count downloaded files and calculate total size
        total_files = 0
        total_size = 0
        
        for ext in ['.mp4', '.mkv', '.webm', '.m4a', '.mp3', '.flv']:
            for file_path in self.base_dir.rglob(f"*{ext}"):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
        
        return {
            'base_directory': str(self.base_dir),
            'active_downloads': len(self.current_downloads),
            'current_downloads': {
                vid: {
                    'title': progress.title,
                    'status': progress.status,
                    'progress_percent': progress.progress_percent,
                    'speed': progress.speed,
                    'eta': progress.eta
                }
                for vid, progress in self.current_downloads.items()
            },
            'file_stats': {
                'total_downloads': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }
        }