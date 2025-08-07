#!/usr/bin/env python3
"""
Test script to check what videos from the configured channel meet the age criteria.
"""

import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, 'src')

from config import load_config
from youtube_client import YouTubeClient
from video_filter import VideoFilter


def main():
    """Test channel video retrieval with simplified age-based filtering."""
    print("🔍 Testing Channel Video Retrieval with Age-Based Filtering")
    print("=" * 65)
    
    try:
        # Load configuration
        config = load_config()
        
        # Test with your configured channel first, then fall back to a test channel
        test_channels = [
            config.youtube.channel_url,
            "https://www.youtube.com/@mkbhd",  # Very active tech channel
            "https://www.youtube.com/@veritasium"  # Active science channel
        ]
        
        print(f"📅 Age filter: Last {config.filters.upload_window_days} days")
        print(f"🎯 Filters: {', '.join(['age-based only', 'no keyword filtering', 'no duration limits'])}")
        
        videos = []
        working_channel = None
        
        for channel_url in test_channels:
            print(f"\n📺 Testing channel: {channel_url}")
            
            # Initialize clients for this channel
            youtube_client = YouTubeClient(config.youtube)
            
            print(f"🔄 Fetching videos from channel...")
            
            # Try API first for better results (recent videos)
            print("   Trying YouTube API...")
            videos = youtube_client.get_channel_videos_api(channel_url, max_results=20)
            
            if not videos:
                print("   API returned no videos, trying RSS feed...")
                videos = youtube_client.get_channel_videos_rss(channel_url, max_results=20)
            
            if videos:
                working_channel = channel_url
                print(f"✅ Found {len(videos)} total videos")
                break
            else:
                print("❌ No videos found from this channel")
        
        if not videos:
            print("\n❌ Could not retrieve videos from any test channel")
            print("   This could indicate:")
            print("   - API key issues")
            print("   - Network connectivity problems") 
            print("   - All test channels are unavailable")
            return False
        
        # Initialize filter
        video_filter = VideoFilter(config.filters)
        
        print(f"\n✅ Using working channel: {working_channel}")
        
        # Show all videos first
        print(f"\n📹 All Recent Videos from Channel:")
        print("-" * 50)
        
        for i, video in enumerate(videos, 1):
            age_days = (datetime.now() - video.published_datetime).days
            status = "✅" if age_days <= config.filters.upload_window_days else "❌"
            
            print(f"{i:2d}. {status} {video.title}")
            print(f"     Published: {video.published_datetime.strftime('%Y-%m-%d %H:%M')} ({age_days} days ago)")
            print(f"     Duration: {video.duration_minutes or 'Unknown'} minutes")
            print(f"     URL: {video.url}")
            print()
        
        # Apply age filter
        print(f"🎯 Applying Age Filter (last {config.filters.upload_window_days} days):")
        print("-" * 45)
        
        filtered_videos = video_filter.filter_by_upload_date(videos)
        
        if filtered_videos:
            print(f"✅ {len(filtered_videos)} videos meet the age criteria:")
            print()
            
            for i, video in enumerate(filtered_videos, 1):
                age_days = (datetime.now() - video.published_datetime).days
                print(f"{i}. 📹 {video.title}")
                print(f"   📅 Published: {video.published_datetime.strftime('%Y-%m-%d %H:%M')} ({age_days} days ago)")
                print(f"   ⏱️  Duration: {video.duration_minutes or 'Unknown'} minutes")
                print(f"   🔗 URL: {video.url}")
                print()
            
            print("🎉 These videos would be downloaded!")
            
        else:
            print(f"❌ No videos found within the last {config.filters.upload_window_days} days")
            
            # Show when the most recent video was published
            if videos:
                most_recent = min(videos, key=lambda v: (datetime.now() - v.published_datetime).days)
                age_days = (datetime.now() - most_recent.published_datetime).days
                print(f"   Most recent video: '{most_recent.title}' ({age_days} days ago)")
                print(f"   Consider increasing upload_window_days to {age_days + 1} to include it")
        
        # Show quota usage
        quota_info = youtube_client.get_quota_usage()
        print(f"\n📊 API Quota Usage: {quota_info['used']}/{quota_info['limit']} units ({quota_info['percentage_used']}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)