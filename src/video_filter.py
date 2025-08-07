import re
from datetime import datetime, timedelta
from typing import List, Optional

from fuzzywuzzy import fuzz
from config import FiltersConfig
from logging_config import LoggerMixin
from youtube_client import YouTubeVideo


class VideoFilter(LoggerMixin):
    """Filters YouTube videos based on configured criteria."""
    
    def __init__(self, config: FiltersConfig):
        self.config = config
    
    def filter_by_upload_date(self, videos: List[YouTubeVideo]) -> List[YouTubeVideo]:
        """Filter videos by upload recency."""
        if self.config.upload_window_days <= 0:
            return videos
        
        cutoff_date = datetime.now() - timedelta(days=self.config.upload_window_days)
        filtered_videos = []
        
        for video in videos:
            if video.published_datetime >= cutoff_date:
                filtered_videos.append(video)
                self.logger.debug(f"Video '{video.title}' passed upload date filter (published: {video.published_datetime})")
            else:
                self.logger.debug(f"Video '{video.title}' filtered out by upload date (published: {video.published_datetime})")
        
        self.logger.info(f"Upload date filter: {len(filtered_videos)}/{len(videos)} videos passed")
        return filtered_videos
    
    def filter_by_title_patterns(self, videos: List[YouTubeVideo]) -> List[YouTubeVideo]:
        """Filter videos by title fuzzy matching."""
        if not self.config.title_patterns:
            return videos
        
        filtered_videos = []
        
        for video in videos:
            title_lower = video.title.lower()
            matched = False
            
            for pattern_config in self.config.title_patterns:
                pattern = pattern_config.pattern.lower()
                threshold = pattern_config.fuzzy_threshold
                
                # Try exact substring match first (faster)
                if pattern in title_lower:
                    matched = True
                    self.logger.debug(f"Video '{video.title}' matched pattern '{pattern}' (exact match)")
                    break
                
                # Fuzzy matching
                similarity = fuzz.partial_ratio(pattern, title_lower)
                if similarity >= threshold:
                    matched = True
                    self.logger.debug(f"Video '{video.title}' matched pattern '{pattern}' (fuzzy: {similarity}% >= {threshold}%)")
                    break
                else:
                    self.logger.debug(f"Video '{video.title}' didn't match pattern '{pattern}' (fuzzy: {similarity}% < {threshold}%)")
            
            if matched:
                filtered_videos.append(video)
        
        self.logger.info(f"Title pattern filter: {len(filtered_videos)}/{len(videos)} videos passed")
        return filtered_videos
    
    def filter_by_duration(self, videos: List[YouTubeVideo]) -> List[YouTubeVideo]:
        """Filter videos by duration constraints."""
        if self.config.min_duration_minutes is None and self.config.max_duration_minutes is None:
            return videos
        
        filtered_videos = []
        
        for video in videos:
            duration_mins = video.duration_minutes
            
            # Skip videos without duration info
            if duration_mins is None:
                self.logger.debug(f"Video '{video.title}' has no duration info, including by default")
                filtered_videos.append(video)
                continue
            
            # Check minimum duration
            if self.config.min_duration_minutes is not None and duration_mins < self.config.min_duration_minutes:
                self.logger.debug(f"Video '{video.title}' filtered out by min duration ({duration_mins} < {self.config.min_duration_minutes} mins)")
                continue
            
            # Check maximum duration
            if self.config.max_duration_minutes is not None and duration_mins > self.config.max_duration_minutes:
                self.logger.debug(f"Video '{video.title}' filtered out by max duration ({duration_mins} > {self.config.max_duration_minutes} mins)")
                continue
            
            filtered_videos.append(video)
            self.logger.debug(f"Video '{video.title}' passed duration filter ({duration_mins} mins)")
        
        self.logger.info(f"Duration filter: {len(filtered_videos)}/{len(videos)} videos passed")
        return filtered_videos
    
    def filter_by_exclude_keywords(self, videos: List[YouTubeVideo]) -> List[YouTubeVideo]:
        """Filter out videos containing excluded keywords."""
        if not self.config.exclude_keywords:
            return videos
        
        filtered_videos = []
        
        for video in videos:
            title_lower = video.title.lower()
            description_lower = video.description.lower()
            excluded = False
            
            for keyword in self.config.exclude_keywords:
                keyword_lower = keyword.lower()
                
                if keyword_lower in title_lower or keyword_lower in description_lower:
                    excluded = True
                    self.logger.debug(f"Video '{video.title}' excluded by keyword '{keyword}'")
                    break
            
            if not excluded:
                filtered_videos.append(video)
                self.logger.debug(f"Video '{video.title}' passed exclude keywords filter")
        
        self.logger.info(f"Exclude keywords filter: {len(filtered_videos)}/{len(videos)} videos passed")
        return filtered_videos
    
    def apply_all_filters(self, videos: List[YouTubeVideo]) -> List[YouTubeVideo]:
        """Apply all configured filters in sequence."""
        self.logger.info(f"Starting to filter {len(videos)} videos")
        
        # Apply filters in order
        filtered_videos = videos
        
        # 1. Upload date filter
        filtered_videos = self.filter_by_upload_date(filtered_videos)
        
        # 2. Title pattern filter
        filtered_videos = self.filter_by_title_patterns(filtered_videos)
        
        # 3. Duration filter
        filtered_videos = self.filter_by_duration(filtered_videos)
        
        # 4. Exclude keywords filter
        filtered_videos = self.filter_by_exclude_keywords(filtered_videos)
        
        self.logger.info(f"Filtering complete: {len(filtered_videos)}/{len(videos)} videos passed all filters")
        
        return filtered_videos
    
    def get_filter_summary(self) -> str:
        """Get a human-readable summary of configured filters."""
        summary = []
        
        if self.config.upload_window_days > 0:
            summary.append(f"Upload window: last {self.config.upload_window_days} days")
        
        if self.config.title_patterns:
            patterns = [f"'{p.pattern}' ({p.fuzzy_threshold}%)" for p in self.config.title_patterns]
            summary.append(f"Title patterns: {', '.join(patterns)}")
        
        if self.config.min_duration_minutes is not None or self.config.max_duration_minutes is not None:
            min_dur = self.config.min_duration_minutes or 0
            max_dur = self.config.max_duration_minutes or "unlimited"
            summary.append(f"Duration: {min_dur}-{max_dur} minutes")
        
        if self.config.exclude_keywords:
            summary.append(f"Exclude keywords: {', '.join(self.config.exclude_keywords)}")
        
        return "; ".join(summary) if summary else "No filters configured"