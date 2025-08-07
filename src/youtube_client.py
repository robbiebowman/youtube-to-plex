import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse, parse_qs

import feedparser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import YouTubeConfig
from logging_config import LoggerMixin, log_performance


class YouTubeVideo:
    """Represents a YouTube video with metadata."""
    
    def __init__(self, video_id: str, title: str, published_at: str, 
                 description: str = "", duration: str = "", 
                 view_count: int = 0, channel_title: str = ""):
        self.video_id = video_id
        self.title = title
        self.published_at = published_at
        self.description = description
        self.duration = duration
        self.view_count = view_count
        self.channel_title = channel_title
        self.url = f"https://www.youtube.com/watch?v={video_id}"
    
    @property
    def published_datetime(self) -> datetime:
        """Parse published_at string to datetime object (timezone-naive)."""
        try:
            # Handle both ISO format and RSS format
            if 'T' in self.published_at:
                # ISO format: 2024-01-15T10:30:00Z
                dt = datetime.fromisoformat(self.published_at.replace('Z', '+00:00'))
                # Convert to naive datetime (remove timezone info)
                return dt.replace(tzinfo=None)
            else:
                # RSS format: Mon, 15 Jan 2024 10:30:00 GMT
                dt = datetime.strptime(self.published_at, '%a, %d %b %Y %H:%M:%S %Z')
                # Convert to naive datetime
                return dt.replace(tzinfo=None)
        except ValueError as e:
            # Fallback to current time if parsing fails
            return datetime.now()
    
    @property
    def duration_minutes(self) -> Optional[int]:
        """Convert ISO 8601 duration to minutes."""
        if not self.duration:
            return None
        
        # Parse ISO 8601 duration format (PT1H30M45S)
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', self.duration)
        if not match:
            return None
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 60 + minutes + (1 if seconds > 0 else 0)  # Round up seconds
    
    def __str__(self):
        return f"YouTubeVideo(id={self.video_id}, title='{self.title[:50]}...', published={self.published_at})"
    
    def __repr__(self):
        return self.__str__()


class YouTubeClient(LoggerMixin):
    """YouTube API client with RSS fallback and quota management."""
    
    def __init__(self, config: YouTubeConfig):
        self.config = config
        self.api_client = None
        self.quota_used = 0
        self.last_quota_reset = datetime.now().date()
        
        # Initialize API client
        try:
            self.api_client = build('youtube', 'v3', developerKey=config.api_key)
            self.logger.info("YouTube API client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize YouTube API client: {e}")
            self.api_client = None
    
    def _check_quota(self, cost: int) -> bool:
        """Check if we have enough quota for the operation."""
        # Reset quota counter daily
        today = datetime.now().date()
        if today > self.last_quota_reset:
            self.quota_used = 0
            self.last_quota_reset = today
            self.logger.info("Daily quota counter reset")
        
        if self.quota_used + cost > self.config.quota_limit:
            self.logger.warning(f"Quota limit would be exceeded. Used: {self.quota_used}, Cost: {cost}, Limit: {self.config.quota_limit}")
            return False
        
        return True
    
    def _extract_channel_id_from_url(self, url: str) -> Optional[str]:
        """Extract channel ID from various YouTube URL formats."""
        # Handle bare @username format (not a full URL)
        if url.startswith('@'):
            username = url[1:]  # Remove @
            return self._get_channel_id_by_search(username)
        
        parsed = urlparse(url)
        
        # Handle @username format: https://www.youtube.com/@username
        if parsed.path.startswith('/@'):
            username = parsed.path[2:]  # Remove /@
            return self._get_channel_id_by_search(username)
        
        # Handle /channel/ format: https://www.youtube.com/channel/UCxxxxx
        if '/channel/' in parsed.path:
            return parsed.path.split('/channel/')[-1]
        
        # Handle /c/ format: https://www.youtube.com/c/channelname
        if '/c/' in parsed.path:
            channel_name = parsed.path.split('/c/')[-1]
            return self._get_channel_id_by_search(channel_name)
        
        # Handle /user/ format: https://www.youtube.com/user/username
        if '/user/' in parsed.path:
            username = parsed.path.split('/user/')[-1]
            return self._get_channel_id_by_username(username)
        
        return None
    
    def _get_channel_id_by_username(self, username: str) -> Optional[str]:
        """Get channel ID by username using API."""
        if not self.api_client or not self._check_quota(1):
            return None
        
        try:
            response = self.api_client.channels().list(
                part='id',
                forUsername=username
            ).execute()
            
            self.quota_used += 1
            
            if response.get('items'):
                channel_id = response['items'][0]['id']
                self.logger.debug(f"Found channel ID {channel_id} for username {username}")
                return channel_id
            
        except HttpError as e:
            self.logger.error(f"Error getting channel ID for username {username}: {e}")
        
        return None
    
    def _get_channel_id_by_search(self, search_term: str) -> Optional[str]:
        """Get channel ID by searching for channel name/username."""
        if not self.api_client or not self._check_quota(100):
            return None
        
        try:
            response = self.api_client.search().list(
                part='snippet',
                q=search_term,
                type='channel',
                maxResults=1
            ).execute()
            
            self.quota_used += 100
            
            if response.get('items'):
                channel_id = response['items'][0]['snippet']['channelId']
                self.logger.debug(f"Found channel ID {channel_id} for search term {search_term}")
                return channel_id
            
        except HttpError as e:
            self.logger.error(f"Error getting channel ID for search term {search_term}: {e}")
        
        return None
    
    @log_performance
    def get_channel_videos_api(self, channel_url: str, max_results: int = 50) -> List[YouTubeVideo]:
        """Get recent videos from channel using YouTube API."""
        if not self.api_client:
            self.logger.warning("YouTube API client not available, falling back to RSS")
            return self.get_channel_videos_rss(channel_url, max_results)
        
        # Extract channel ID from URL
        channel_id = self._extract_channel_id_from_url(channel_url)
        if not channel_id:
            self.logger.error(f"Could not extract channel ID from URL: {channel_url}")
            return []
        
        # Check quota for search operation (100 units)
        if not self._check_quota(100):
            self.logger.warning("Quota limit reached, falling back to RSS")
            return self.get_channel_videos_rss(channel_url, max_results)
        
        videos = []
        
        try:
            # Search for recent videos from the channel
            search_response = self.api_client.search().list(
                part='snippet',
                channelId=channel_id,
                type='video',
                order='date',
                maxResults=min(max_results, 50)  # API limit is 50
            ).execute()
            
            self.quota_used += 100
            
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            
            if video_ids:
                # Get detailed video information (1 unit per video)
                if self._check_quota(len(video_ids)):
                    videos_response = self.api_client.videos().list(
                        part='snippet,contentDetails,statistics',
                        id=','.join(video_ids)
                    ).execute()
                    
                    self.quota_used += len(video_ids)
                    
                    for video_data in videos_response.get('items', []):
                        video = YouTubeVideo(
                            video_id=video_data['id'],
                            title=video_data['snippet']['title'],
                            published_at=video_data['snippet']['publishedAt'],
                            description=video_data['snippet'].get('description', ''),
                            duration=video_data['contentDetails'].get('duration', ''),
                            view_count=int(video_data['statistics'].get('viewCount', 0)),
                            channel_title=video_data['snippet']['channelTitle']
                        )
                        videos.append(video)
                else:
                    # Create basic video objects without detailed info
                    for item in search_response.get('items', []):
                        video = YouTubeVideo(
                            video_id=item['id']['videoId'],
                            title=item['snippet']['title'],
                            published_at=item['snippet']['publishedAt'],
                            description=item['snippet'].get('description', ''),
                            channel_title=item['snippet']['channelTitle']
                        )
                        videos.append(video)
            
            self.logger.info(f"Retrieved {len(videos)} videos from API for channel {channel_id}")
            
        except HttpError as e:
            self.logger.error(f"YouTube API error: {e}")
            # Fall back to RSS on API error
            return self.get_channel_videos_rss(channel_url, max_results)
        
        return videos
    
    @log_performance
    def get_channel_videos_rss(self, channel_url: str, max_results: int = 50) -> List[YouTubeVideo]:
        """Get recent videos from channel using RSS feed (no quota cost)."""
        # Extract channel ID or username from URL
        channel_id = self._extract_channel_id_from_url(channel_url)
        
        # Construct RSS feed URL
        if channel_id and channel_id.startswith('UC'):
            # Channel ID format
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        else:
            # Try username format (extract from @username)
            parsed = urlparse(channel_url)
            if parsed.path.startswith('/@'):
                username = parsed.path[2:]
                rss_url = f"https://www.youtube.com/feeds/videos.xml?user={username}"
            else:
                self.logger.error(f"Could not determine RSS feed URL for: {channel_url}")
                return []
        
        videos = []
        
        try:
            self.logger.debug(f"Fetching RSS feed: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                self.logger.warning(f"RSS feed parsing warning: {feed.bozo_exception}")
            
            for entry in feed.entries[:max_results]:
                # Extract video ID from link
                video_id = entry.yt_videoid if hasattr(entry, 'yt_videoid') else entry.link.split('v=')[-1]
                
                video = YouTubeVideo(
                    video_id=video_id,
                    title=entry.title,
                    published_at=entry.published,
                    description=entry.get('summary', ''),
                    channel_title=feed.feed.get('title', '')
                )
                videos.append(video)
            
            self.logger.info(f"Retrieved {len(videos)} videos from RSS for channel")
            
        except Exception as e:
            self.logger.error(f"RSS feed parsing error: {e}")
        
        return videos
    
    def get_channel_videos(self, channel_url: str, max_results: int = 50, prefer_api: bool = True) -> List[YouTubeVideo]:
        """Get recent videos from channel with automatic fallback."""
        if prefer_api and self.api_client:
            videos = self.get_channel_videos_api(channel_url, max_results)
            if videos:  # API succeeded
                return videos
        
        # Fall back to RSS
        return self.get_channel_videos_rss(channel_url, max_results)
    
    def get_quota_usage(self) -> Dict[str, Union[int, str]]:
        """Get current quota usage information."""
        return {
            'used': self.quota_used,
            'limit': self.config.quota_limit,
            'remaining': self.config.quota_limit - self.quota_used,
            'reset_date': self.last_quota_reset.isoformat(),
            'percentage_used': round((self.quota_used / self.config.quota_limit) * 100, 2)
        }