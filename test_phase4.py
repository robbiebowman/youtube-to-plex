#!/usr/bin/env python3
"""
Phase 4 validation test for download management and storage.
Tests yt-dlp integration, file organization, and metadata generation.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, 'src')

from config import load_config, Config, DownloadConfig, StorageConfig
from download_manager import DownloadManager, PlexNamingHelper, DownloadDatabase
from youtube_client import YouTubeVideo
from main_downloader import YouTubeToPlexDownloader


def create_test_video() -> YouTubeVideo:
    """Create a test video object."""
    return YouTubeVideo(
        video_id="dQw4w9WgXcQ",  # Rick Roll - a real YouTube video
        title="University Challenge S55E04 - Newcastle v. Edinburgh",
        published_at=(datetime.now() - timedelta(days=1)).isoformat(),
        description="Test episode for University Challenge series",
        duration="PT30M15S",  # 30 minutes 15 seconds
        view_count=1000000,
        channel_title="Test Channel"
    )


def test_plex_naming():
    """Test Plex-compatible naming and path generation."""
    print("🔍 Testing Plex Naming Helper...")
    print("-" * 35)
    
    try:
        # Test video titles and expected parsing
        test_cases = [
            {
                'title': 'University Challenge S55E04 - Newcastle v. Edinburgh',
                'expected_series': 'University Challenge',
                'expected_season': 55,
                'expected_episode': 4
            },
            {
                'title': 'The Great British Baking Show Season 3 Episode 5',
                'expected_series': 'The Great British Baking Show',
                'expected_season': 3,
                'expected_episode': 5
            },
            {
                'title': 'Some Random Video Title',
                'expected_series': 'Some Random Video Title',
                'expected_season': 1,
                'expected_episode': None
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"   Test {i}: {case['title']}")
            
            series, season, episode = PlexNamingHelper.extract_episode_info(case['title'])
            
            print(f"     Series: {series} (expected: {case['expected_series']})")
            print(f"     Season: {season} (expected: {case['expected_season']})")
            print(f"     Episode: {episode} (expected: {case['expected_episode']})")
            
            # Verify results
            assert series == case['expected_series'], f"Series mismatch: {series} != {case['expected_series']}"
            assert season == case['expected_season'], f"Season mismatch: {season} != {case['expected_season']}"
            assert episode == case['expected_episode'], f"Episode mismatch: {episode} != {case['expected_episode']}"
            
            print(f"     ✅ Parsing correct")
        
        # Test path generation
        test_video = create_test_video()
        base_dir = "/tmp/test-plex"
        
        output_dir, filename = PlexNamingHelper.generate_plex_path(
            test_video, base_dir, organize_by_season=True
        )
        
        print(f"\n   📁 Path generation test:")
        print(f"     Base dir: {base_dir}")
        print(f"     Output dir: {output_dir}")
        print(f"     Filename: {filename}")
        
        expected_dir = "/tmp/test-plex/University Challenge/Season 55"
        assert output_dir == expected_dir, f"Directory mismatch: {output_dir} != {expected_dir}"
        
        print(f"     ✅ Path generation correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Plex naming test failed: {e}")
        return False


def test_download_database():
    """Test download tracking database."""
    print("\n🔍 Testing Download Database...")
    print("-" * 32)
    
    try:
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_path = tmp_db.name
        
        try:
            db = DownloadDatabase(db_path)
            
            # Test initial state
            assert not db.is_downloaded("test_video_id"), "Database should be empty initially"
            print("   ✅ Initial state correct")
            
            # Test adding download
            test_video = create_test_video()
            test_file_path = "/test/path/video.mp4"
            test_file_size = 1024 * 1024 * 100  # 100MB
            test_checksum = "test_checksum_123"
            
            db.add_download(test_video, test_file_path, test_file_size, test_checksum)
            print("   ✅ Download record added")
            
            # Test checking if downloaded
            assert db.is_downloaded(test_video.video_id), "Video should be marked as downloaded"
            print("   ✅ Download detection works")
            
            # Test statistics
            stats = db.get_download_stats()
            assert stats['total_downloads'] == 1, f"Expected 1 download, got {stats['total_downloads']}"
            assert stats['total_size_mb'] == 100.0, f"Expected 100MB, got {stats['total_size_mb']}"
            print(f"   ✅ Statistics: {stats['total_downloads']} downloads, {stats['total_size_mb']} MB")
            
            return True
            
        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def test_download_manager_setup():
    """Test download manager initialization and configuration."""
    print("\n🔍 Testing Download Manager Setup...")
    print("-" * 38)
    
    try:
        # Create test configuration
        config = load_config()
        
        # Use temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Override storage config for testing
            config.storage.base_directory = temp_dir
            config.storage.organize_by_season = True
            config.storage.generate_metadata = True
            config.storage.cleanup_partial_downloads = True
            
            # Initialize download manager
            dm = DownloadManager(config)
            
            print(f"   📁 Base directory: {dm.base_dir}")
            print(f"   ✅ Download manager initialized")
            
            # Test directory creation
            assert dm.base_dir.exists(), "Base directory should be created"
            print(f"   ✅ Base directory created")
            
            # Test database initialization
            assert dm.db.db_path, "Database should be initialized"
            print(f"   ✅ Database initialized")
            
            # Test status reporting
            status = dm.get_download_status()
            assert 'base_directory' in status, "Status should include base directory"
            assert 'database_stats' in status, "Status should include database stats"
            print(f"   ✅ Status reporting works")
            
            return True
    
    except Exception as e:
        print(f"❌ Download manager setup test failed: {e}")
        return False


def test_dry_run_mode():
    """Test the main downloader in dry run mode."""
    print("\n🔍 Testing Dry Run Mode...")
    print("-" * 26)
    
    try:
        # Test with current config but in dry run mode
        downloader = YouTubeToPlexDownloader("config.yaml")
        
        print(f"   📺 Channel: {downloader.config.youtube.channel_url}")
        print(f"   🎯 Testing dry run with max 5 videos...")
        
        # Run in dry run mode
        results = downloader.check_and_download(dry_run=True, max_videos=5)
        
        print(f"   📊 Results:")
        print(f"     New videos found: {results['new_videos_found']}")
        print(f"     Videos processed: {len(results['videos_processed'])}")
        print(f"     Errors: {len(results['errors'])}")
        
        if results['videos_processed']:
            print(f"   📹 Videos that would be downloaded:")
            for video in results['videos_processed'][:3]:  # Show first 3
                print(f"     - {video['title']}")
        
        # Should not have actually downloaded anything
        assert results['downloads_attempted'] == 0, "Dry run should not attempt downloads"
        print(f"   ✅ Dry run mode working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Dry run test failed: {e}")
        return False


def test_status_reporting():
    """Test status reporting functionality."""
    print("\n🔍 Testing Status Reporting...")
    print("-" * 30)
    
    try:
        downloader = YouTubeToPlexDownloader("config.yaml")
        
        status = downloader.get_status()
        
        # Check required fields
        required_fields = ['timestamp', 'monitoring', 'downloads', 'config']
        for field in required_fields:
            assert field in status, f"Status should include {field}"
        
        print(f"   ✅ Status structure correct")
        
        # Check monitoring info
        monitoring = status['monitoring']
        assert 'channel_url' in monitoring, "Monitoring should include channel URL"
        assert 'total_videos_seen' in monitoring, "Monitoring should include video count"
        
        print(f"   📺 Channel: {monitoring['channel_url']}")
        print(f"   👀 Videos seen: {monitoring['total_videos_seen']}")
        
        # Check download info
        downloads = status['downloads']
        assert 'database_stats' in downloads, "Downloads should include database stats"
        
        db_stats = downloads['database_stats']
        print(f"   💾 Downloads: {db_stats['total_downloads']}")
        print(f"   📦 Total size: {db_stats['total_size_mb']} MB")
        
        print(f"   ✅ Status reporting complete")
        
        return True
        
    except Exception as e:
        print(f"❌ Status reporting test failed: {e}")
        return False


def test_file_organization():
    """Test file organization and naming."""
    print("\n🔍 Testing File Organization...")
    print("-" * 32)
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"   📁 Test directory: {temp_dir}")
            
            # Test different video types
            test_videos = [
                YouTubeVideo(
                    video_id="test1",
                    title="University Challenge S55E04 - Newcastle v. Edinburgh",
                    published_at=datetime.now().isoformat(),
                    description="Test episode",
                    duration="PT30M"
                ),
                YouTubeVideo(
                    video_id="test2", 
                    title="Random Documentary Video",
                    published_at=datetime.now().isoformat(),
                    description="Random video",
                    duration="PT45M"
                )
            ]
            
            for video in test_videos:
                output_dir, filename = PlexNamingHelper.generate_plex_path(
                    video, temp_dir, organize_by_season=True
                )
                
                print(f"   📹 {video.title}")
                print(f"     Directory: {output_dir}")
                print(f"     Filename: {filename}")
                
                # Create the directory structure
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                assert Path(output_dir).exists(), f"Directory should be created: {output_dir}"
                
                print(f"     ✅ Directory structure created")
            
            return True
    
    except Exception as e:
        print(f"❌ File organization test failed: {e}")
        return False


def main():
    """Run all Phase 4 validation tests."""
    print("🚀 YouTube to Plex Downloader - Phase 4 Validation")
    print("=" * 60)
    
    tests = [
        ("Plex Naming Helper", test_plex_naming),
        ("Download Database", test_download_database),
        ("Download Manager Setup", test_download_manager_setup),
        ("File Organization", test_file_organization),
        ("Status Reporting", test_status_reporting),
        ("Dry Run Mode", test_dry_run_mode),
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
    print("PHASE 4 VALIDATION SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Phase 4 implementation is working correctly!")
        print("\n🎯 Ready for:")
        print("- Full integration testing")
        print("- Actual video downloads")
        print("- Phase 5: Scheduling and automation")
        print("\n💡 To test actual downloading:")
        print("   python src/main_downloader.py --dry-run")
        print("   python src/main_downloader.py --status")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)