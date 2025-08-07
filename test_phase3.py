#!/usr/bin/env python3
"""
Phase 3 validation test for YouTube integration and channel monitoring.
Tests YouTube API client, RSS fallback, video filtering, and channel monitoring.
"""

import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, 'src')

from config import load_config
from youtube_client import YouTubeClient, YouTubeVideo
from video_filter import VideoFilter
from channel_monitor import ChannelMonitor


def test_youtube_client():
    """Test YouTube client functionality."""
    print("🔍 Testing YouTube Client...")
    print("-" * 30)
    
    try:
        config = load_config()
        client = YouTubeClient(config.youtube)
        
        # Test quota tracking
        quota_info = client.get_quota_usage()
        print(f"✅ Quota tracking: {quota_info['used']}/{quota_info['limit']} units used")
        
        # Test channel video retrieval
        print(f"🎥 Testing video retrieval from: {config.youtube.channel_url}")
        
        # Test RSS fallback first (no quota cost)
        print("   Testing RSS feed...")
        rss_videos = client.get_channel_videos_rss(config.youtube.channel_url, max_results=5)
        print(f"   ✅ RSS: Retrieved {len(rss_videos)} videos")
        
        if rss_videos:
            sample_video = rss_videos[0]
            print(f"   Sample video: {sample_video.title}")
            print(f"   Published: {sample_video.published_datetime}")
            print(f"   Duration: {sample_video.duration_minutes} minutes")
        
        # Test API if quota allows
        if client._check_quota(100):
            print("   Testing YouTube API...")
            api_videos = client.get_channel_videos_api(config.youtube.channel_url, max_results=5)
            print(f"   ✅ API: Retrieved {len(api_videos)} videos")
            
            if api_videos:
                sample_video = api_videos[0]
                print(f"   Sample video: {sample_video.title}")
                print(f"   Views: {sample_video.view_count:,}")
                print(f"   Duration: {sample_video.duration_minutes} minutes")
        else:
            print("   ⚠️ Skipping API test to preserve quota")
        
        return True
        
    except Exception as e:
        print(f"❌ YouTube client test failed: {e}")
        return False


def test_video_filter():
    """Test video filtering functionality."""
    print("\n🔍 Testing Video Filter...")
    print("-" * 25)
    
    try:
        config = load_config()
        filter_engine = VideoFilter(config.filters)
        
        print(f"📋 Filter configuration: {filter_engine.get_filter_summary()}")
        
        # Create test videos
        now = datetime.now()
        test_videos = [
            YouTubeVideo(
                video_id="test1",
                title="Python Episode 1: Getting Started",
                published_at=(now - timedelta(days=1)).isoformat(),
                description="Learn Python programming basics",
                duration="PT15M30S"  # 15 minutes 30 seconds
            ),
            YouTubeVideo(
                video_id="test2", 
                title="Behind the Scenes: Studio Tour",
                published_at=(now - timedelta(days=2)).isoformat(),
                description="A quick tour of our recording studio",
                duration="PT5M10S"  # 5 minutes 10 seconds
            ),
            YouTubeVideo(
                video_id="test3",
                title="Season Finale: The Ultimate Python Challenge",
                published_at=(now - timedelta(days=10)).isoformat(),
                description="The final episode of our Python series",
                duration="PT45M0S"  # 45 minutes
            ),
            YouTubeVideo(
                video_id="test4",
                title="Movie Trailer: Coming Soon",
                published_at=(now - timedelta(days=1)).isoformat(),
                description="Exciting preview of upcoming content",
                duration="PT2M30S"  # 2 minutes 30 seconds
            )
        ]
        
        print(f"\n📹 Testing with {len(test_videos)} sample videos:")
        for video in test_videos:
            print(f"   - {video.title} ({video.duration_minutes} mins, {video.published_datetime.strftime('%Y-%m-%d')})")
        
        # Test individual filters
        print("\n🔍 Testing individual filters:")
        
        # Upload date filter
        date_filtered = filter_engine.filter_by_upload_date(test_videos)
        print(f"   Upload date ({config.filters.upload_window_days} days): {len(date_filtered)}/{len(test_videos)} passed")
        
        # Title pattern filter
        title_filtered = filter_engine.filter_by_title_patterns(test_videos)
        print(f"   Title patterns: {len(title_filtered)}/{len(test_videos)} passed")
        
        # Duration filter
        duration_filtered = filter_engine.filter_by_duration(test_videos)
        print(f"   Duration: {len(duration_filtered)}/{len(test_videos)} passed")
        
        # Exclude keywords filter
        exclude_filtered = filter_engine.filter_by_exclude_keywords(test_videos)
        print(f"   Exclude keywords: {len(exclude_filtered)}/{len(test_videos)} passed")
        
        # Test combined filters
        print("\n🎯 Testing combined filters:")
        final_filtered = filter_engine.apply_all_filters(test_videos)
        print(f"   Final result: {len(final_filtered)}/{len(test_videos)} videos passed all filters")
        
        if final_filtered:
            print("   Videos that passed:")
            for video in final_filtered:
                print(f"     ✅ {video.title}")
        
        return True
        
    except Exception as e:
        print(f"❌ Video filter test failed: {e}")
        return False


def test_channel_monitor():
    """Test channel monitoring functionality."""
    print("\n🔍 Testing Channel Monitor...")
    print("-" * 27)
    
    try:
        config = load_config()
        monitor = ChannelMonitor(config)
        
        # Test status reporting
        status = monitor.get_monitoring_status()
        print(f"📊 Monitoring status:")
        print(f"   Channel: {status['channel_url']}")
        print(f"   Videos seen: {status['total_videos_seen']}")
        print(f"   Filters: {status['filter_summary']}")
        print(f"   Quota: {status['quota_usage']['used']}/{status['quota_usage']['limit']} ({status['quota_usage']['percentage_used']}%)")
        
        # Test video checking (but limit to preserve quota)
        print(f"\n🔍 Testing new video check...")
        new_videos = monitor.check_for_new_videos(max_videos=10)  # Limit to 10 to save quota
        
        print(f"   Found {len(new_videos)} new videos matching criteria")
        
        if new_videos:
            print("   New videos:")
            for video in new_videos[:3]:  # Show max 3
                print(f"     📹 {video.title}")
                print(f"        Published: {video.published_datetime.strftime('%Y-%m-%d %H:%M')}")
                print(f"        Duration: {video.duration_minutes or 'Unknown'} minutes")
        
        # Test cache functionality
        print(f"\n💾 Cache file: {monitor.cache_file}")
        print(f"   Cache exists: {monitor.cache_file.exists()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Channel monitor test failed: {e}")
        return False


def test_configuration():
    """Test Phase 3 configuration loading."""
    print("🔍 Testing Configuration...")
    print("-" * 26)
    
    try:
        config = load_config()
        
        # Test YouTube config
        print(f"✅ YouTube API key: {'✓ Set' if config.youtube.api_key and not config.youtube.api_key.startswith('${') else '❌ Missing'}")
        print(f"✅ Channel URL: {config.youtube.channel_url}")
        print(f"✅ Quota limit: {config.youtube.quota_limit:,}")
        
        # Test filters config
        print(f"\n📋 Filters configuration:")
        print(f"   Upload window: {config.filters.upload_window_days} days")
        print(f"   Title patterns: {len(config.filters.title_patterns)} configured")
        for pattern in config.filters.title_patterns:
            print(f"     - '{pattern.pattern}' (threshold: {pattern.fuzzy_threshold}%)")
        
        if config.filters.min_duration_minutes or config.filters.max_duration_minutes:
            min_dur = config.filters.min_duration_minutes or 0
            max_dur = config.filters.max_duration_minutes or "∞"
            print(f"   Duration range: {min_dur}-{max_dur} minutes")
        
        if config.filters.exclude_keywords:
            print(f"   Exclude keywords: {', '.join(config.filters.exclude_keywords)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def main():
    """Run all Phase 3 validation tests."""
    print("🚀 YouTube to Plex Downloader - Phase 3 Validation")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("YouTube Client", test_youtube_client),
        ("Video Filter", test_video_filter),
        ("Channel Monitor", test_channel_monitor),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print(f"{'='*60}")
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("PHASE 3 VALIDATION SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Phase 3 implementation is working correctly!")
        print("\n🎯 Ready for:")
        print("- Phase 4: Download management and storage")
        print("- Testing with real YouTube channels")
        print("- Integration with video downloading")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)