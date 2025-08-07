from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config import Config
from logging_config import LoggerMixin, log_performance
from youtube_client import YouTubeClient, YouTubeVideo
from video_filter import VideoFilter


class ChannelMonitor(LoggerMixin):
    """Monitors YouTube channel for new videos matching criteria."""
    
    def __init__(self, config: Config):
        self.config = config
        self.youtube_client = YouTubeClient(config.youtube)
        self.video_filter = VideoFilter(config.filters)
    
# Video caching removed - using file existence checking instead
    
    @log_performance
    def check_for_new_videos(self, max_videos: int = 50) -> List[YouTubeVideo]:
        """Check channel for new videos matching criteria."""
        self.logger.info(f"Checking channel for new videos: {self.config.youtube.channel_url}")
        
        # Get recent videos from channel
        all_videos = self.youtube_client.get_channel_videos(
            self.config.youtube.channel_url, 
            max_results=max_videos
        )
        
        if not all_videos:
            self.logger.warning("No videos retrieved from channel")
            return []
        
        self.logger.info(f"Retrieved {len(all_videos)} videos from channel")
        
        # Apply content filters
        self.logger.info(f"Applying filters: {self.video_filter.get_filter_summary()}")
        filtered_videos = self.video_filter.apply_all_filters(all_videos)
        
        if filtered_videos:
            self.logger.info(f"Found {len(filtered_videos)} videos matching criteria:")
            for video in filtered_videos:
                self.logger.info(f"  - {video.title} ({video.published_datetime.strftime('%Y-%m-%d %H:%M')})")
        else:
            self.logger.info("No videos match the configured criteria")
        
        return filtered_videos
    
    def force_check_video(self, video_id: str) -> Optional[YouTubeVideo]:
        """Force check a specific video, bypassing seen cache."""
        self.logger.info(f"Force checking video: {video_id}")
        
        try:
            # Get video details via API
            if self.youtube_client.api_client and self.youtube_client._check_quota(1):
                response = self.youtube_client.api_client.videos().list(
                    part='snippet,contentDetails,statistics',
                    id=video_id
                ).execute()
                
                self.youtube_client.quota_used += 1
                
                if response.get('items'):
                    video_data = response['items'][0]
                    video = YouTubeVideo(
                        video_id=video_data['id'],
                        title=video_data['snippet']['title'],
                        published_at=video_data['snippet']['publishedAt'],
                        description=video_data['snippet'].get('description', ''),
                        duration=video_data['contentDetails'].get('duration', ''),
                        view_count=int(video_data['statistics'].get('viewCount', 0)),
                        channel_title=video_data['snippet']['channelTitle']
                    )
                    
                    # Apply filters
                    filtered_videos = self.video_filter.apply_all_filters([video])
                    return filtered_videos[0] if filtered_videos else None
            
        except Exception as e:
            self.logger.error(f"Error checking video {video_id}: {e}")
        
        return None
    
    def get_monitoring_status(self) -> dict:
        """Get current monitoring status and statistics."""
        quota_info = self.youtube_client.get_quota_usage()
        
        return {
            'channel_url': self.config.youtube.channel_url,
            'filter_summary': self.video_filter.get_filter_summary(),
            'quota_usage': quota_info,
            'last_check': datetime.now().isoformat()
        }
    
# Cache methods removed - no longer needed with file-based duplicate detection