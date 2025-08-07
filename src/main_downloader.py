#!/usr/bin/env python3
"""
Main YouTube to Plex downloader application.
Integrates channel monitoring, filtering, and downloading.
"""

import sys
from datetime import datetime
from typing import List

from config import load_config
from logging_config import setup_logging, LoggerMixin
from channel_monitor import ChannelMonitor
from download_manager import DownloadManager
from youtube_client import YouTubeVideo


class YouTubeToPlexDownloader(LoggerMixin):
    """Main application class that orchestrates the download process."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the downloader with configuration."""
        self.config = load_config(config_path)
        
        # Set up logging
        setup_logging(self.config.logging)
        
        # Initialize components
        self.monitor = ChannelMonitor(self.config)
        self.download_manager = DownloadManager(self.config)
        
        self.logger.info("YouTube to Plex Downloader initialized")
        self.logger.info(f"Monitoring channel: {self.config.youtube.channel_url}")
        self.logger.info(f"Download directory: {self.config.storage.base_directory}")
    
    def check_and_download(self, dry_run: bool = False, max_videos: int = 50) -> dict:
        """Check for new videos and download them."""
        self.logger.info("Starting check and download process")
        
        results = {
            'new_videos_found': 0,
            'downloads_attempted': 0,
            'downloads_successful': 0,
            'downloads_failed': 0,
            'videos_processed': [],
            'errors': []
        }
        
        try:
            # Check for new videos
            self.logger.info("Checking for new videos...")
            new_videos = self.monitor.check_for_new_videos(max_videos=max_videos)
            results['new_videos_found'] = len(new_videos)
            
            if not new_videos:
                self.logger.info("No new videos found matching criteria")
                return results
            
            self.logger.info(f"Found {len(new_videos)} new videos to download")
            
            # List videos that will be downloaded
            for video in new_videos:
                video_info = {
                    'video_id': video.video_id,
                    'title': video.title,
                    'published': video.published_datetime.isoformat(),
                    'duration_minutes': video.duration_minutes,
                    'url': video.url,
                    'download_status': 'pending'
                }
                results['videos_processed'].append(video_info)
            
            if dry_run:
                self.logger.info("DRY RUN: Would download the following videos:")
                for video in new_videos:
                    self.logger.info(f"  - {video.title}")
                return results
            
            # Download videos
            self.logger.info("Starting downloads...")
            results['downloads_attempted'] = len(new_videos)
            
            def progress_callback(progress):
                """Callback for download progress updates."""
                self.logger.info(f"Download progress: {progress.title} - {progress.status}")
            
            download_results = self.download_manager.download_videos(
                new_videos, 
                progress_callback=progress_callback
            )
            
            # Update results
            for video_info in results['videos_processed']:
                video_id = video_info['video_id']
                if video_id in download_results:
                    success = download_results[video_id]
                    video_info['download_status'] = 'success' if success else 'failed'
                    
                    if success:
                        results['downloads_successful'] += 1
                    else:
                        results['downloads_failed'] += 1
            
            # Clean up partial downloads
            self.download_manager.cleanup_partial_downloads()
            
            self.logger.info(f"Download process complete: {results['downloads_successful']}/{results['downloads_attempted']} successful")
            
        except Exception as e:
            error_msg = f"Error in check and download process: {e}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def get_status(self) -> dict:
        """Get current status of the downloader."""
        monitor_status = self.monitor.get_monitoring_status()
        download_status = self.download_manager.get_download_status()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'monitoring': monitor_status,
            'downloads': download_status,
            'config': {
                'channel_url': self.config.youtube.channel_url,
                'upload_window_days': self.config.filters.upload_window_days,
                'base_directory': self.config.storage.base_directory,
                'organize_by_season': self.config.storage.organize_by_season,
                'generate_metadata': self.config.storage.generate_metadata
            }
        }
    
    def force_download_video(self, video_url: str) -> bool:
        """Force download a specific video by URL."""
        self.logger.info(f"Force downloading video: {video_url}")
        
        try:
            # Extract video ID from URL
            video_id = video_url.split('v=')[-1].split('&')[0]
            
            # Get video info via API
            video = self.monitor.force_check_video(video_id)
            if not video:
                self.logger.error(f"Could not get video information for {video_id}")
                return False
            
            # Check if it's already downloaded
            if self.download_manager.is_already_downloaded(video):
                self.logger.warning(f"Video '{video.title}' already downloaded")
                return True
            
            # Download the video
            success = self.download_manager.download_video(video)
            
            if success:
                self.logger.info(f"Successfully force downloaded: {video.title}")
            else:
                self.logger.error(f"Failed to force download: {video.title}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error in force download: {e}")
            return False


def main():
    """Main entry point for the application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube to Plex Downloader")
    parser.add_argument("--config", default="config.yaml", help="Path to configuration file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded without downloading")
    parser.add_argument("--max-videos", type=int, default=50, help="Maximum videos to check")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--force-download", help="Force download a specific video URL")
# Cache reset option removed - no longer needed
    
    args = parser.parse_args()
    
    try:
        # Initialize downloader
        downloader = YouTubeToPlexDownloader(args.config)
        
        if args.status:
            # Show status
            status = downloader.get_status()
            print("=" * 60)
            print("YOUTUBE TO PLEX DOWNLOADER STATUS")
            print("=" * 60)
            print(f"Timestamp: {status['timestamp']}")
            print(f"Channel: {status['config']['channel_url']}")
            print(f"Filter: Last {status['config']['upload_window_days']} days")
            print(f"Downloads: {status['downloads']['file_stats']['total_downloads']}")
            print(f"Total size: {status['downloads']['file_stats']['total_size_mb']} MB")
            print(f"Active downloads: {status['downloads']['active_downloads']}")
            return
        
        if args.force_download:
            # Force download specific video
            success = downloader.force_download_video(args.force_download)
            if success:
                print("✅ Video downloaded successfully")
            else:
                print("❌ Video download failed")
                sys.exit(1)
            return
        
        # Main download process
        print("🚀 YouTube to Plex Downloader")
        print("=" * 40)
        
        if args.dry_run:
            print("🧪 DRY RUN MODE - No files will be downloaded")
        
        results = downloader.check_and_download(
            dry_run=args.dry_run, 
            max_videos=args.max_videos
        )
        
        # Print results
        print(f"\n📊 Results:")
        print(f"   New videos found: {results['new_videos_found']}")
        
        if not args.dry_run:
            print(f"   Downloads attempted: {results['downloads_attempted']}")
            print(f"   Downloads successful: {results['downloads_successful']}")
            print(f"   Downloads failed: {results['downloads_failed']}")
        
        if results['videos_processed']:
            print(f"\n📹 Videos processed:")
            for video in results['videos_processed']:
                status_icon = "✅" if video['download_status'] == 'success' else "❌" if video['download_status'] == 'failed' else "⏳"
                print(f"   {status_icon} {video['title']}")
        
        if results['errors']:
            print(f"\n❌ Errors:")
            for error in results['errors']:
                print(f"   {error}")
            sys.exit(1)
        
        print("\n✨ Process completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()