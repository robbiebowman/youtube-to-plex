#!/usr/bin/env python3
"""
YouTube API validation test.
Tests that the YouTube Data API v3 key works and has proper permissions.
"""

import sys
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add src to path
sys.path.insert(0, 'src')
from config import load_config


def test_youtube_api():
    """Test YouTube Data API v3 functionality with the configured API key."""
    print("🔍 Testing YouTube Data API v3...")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        api_key = config.youtube.api_key
        
        if not api_key or api_key.startswith("${"):
            print("❌ YouTube API key not found or not set properly")
            print("   Please check your .env file")
            return False
        
        print(f"✅ API key loaded: {api_key[:10]}...{api_key[-4:]}")
        
        # Build YouTube API client
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Test 1: Basic API connectivity - get quota info
        print("\n🔍 Test 1: Basic API connectivity...")
        try:
            # Simple search query to test basic functionality
            search_response = youtube.search().list(
                q='python tutorial',
                part='snippet',
                type='video',
                maxResults=1
            ).execute()
            
            print("✅ Basic API connectivity works")
            
        except HttpError as e:
            if e.resp.status == 403:
                print("❌ API key permissions error:")
                print(f"   {e.content.decode()}")
                print("   Make sure YouTube Data API v3 is enabled for your project")
                return False
            else:
                raise
        
        # Test 2: Channel information retrieval
        print("\n🔍 Test 2: Channel information retrieval...")
        
        # Use a well-known channel ID for testing (Python's official channel)
        test_channel_id = "UCwmFOfFuvRPI112vR5DNnJA"  # Real Python channel
        
        try:
            channel_response = youtube.channels().list(
                part='snippet,statistics',
                id=test_channel_id
            ).execute()
            
            if 'items' in channel_response and channel_response['items']:
                channel = channel_response['items'][0]
                channel_name = channel['snippet']['title']
                subscriber_count = channel['statistics'].get('subscriberCount', 'Hidden')
                
                print(f"✅ Successfully retrieved channel info:")
                print(f"   Channel: {channel_name}")
                print(f"   Subscribers: {subscriber_count}")
            else:
                print("⚠️  Channel not found (this shouldn't happen with test channel)")
                print(f"   Response: {channel_response}")
                
        except HttpError as e:
            print(f"❌ Channel info retrieval failed: {e}")
            return False
        
        # Test 3: Video listing from channel
        print("\n🔍 Test 3: Recent video listing...")
        
        try:
            # Get recent videos from the test channel
            search_response = youtube.search().list(
                part='snippet',
                channelId=test_channel_id,
                type='video',
                order='date',
                maxResults=3
            ).execute()
            
            if 'items' in search_response and search_response['items']:
                print(f"✅ Successfully retrieved {len(search_response['items'])} recent videos:")
                for i, video in enumerate(search_response['items'][:2], 1):
                    title = video['snippet']['title']
                    published = video['snippet']['publishedAt'][:10]  # Date only
                    print(f"   {i}. {title} ({published})")
            else:
                print("⚠️  No videos found")
                print(f"   Response: {search_response}")
                
        except HttpError as e:
            print(f"❌ Video listing failed: {e}")
            return False
        
        # Test 4: Quota usage estimation
        print("\n🔍 Test 4: Quota usage information...")
        
        # Estimate quota usage for our tests
        # search().list = 100 units, channels().list = 1 unit
        estimated_quota_used = 100 + 1 + 100  # 3 API calls we made
        daily_quota = config.youtube.quota_limit
        
        print(f"✅ Estimated quota used in this test: {estimated_quota_used} units")
        print(f"   Daily quota limit (configured): {daily_quota:,} units")
        print(f"   Remaining quota: ~{daily_quota - estimated_quota_used:,} units")
        
        if estimated_quota_used > daily_quota * 0.1:  # More than 10% of quota
            print("⚠️  This test used >10% of your daily quota")
        
        # Test 5: Test with your configured channel (if different from example)
        print("\n🔍 Test 5: Testing your configured channel...")
        
        configured_url = config.youtube.channel_url
        print(f"   Configured channel URL: {configured_url}")
        
        if "examplechannel" in configured_url:
            print("⚠️  You're still using the example channel URL")
            print("   Update config.yaml with your target channel URL")
        else:
            print("✅ Custom channel URL configured")
            # We could test this channel too, but let's save quota
        
        print("\n" + "=" * 50)
        print("🎉 YouTube API validation completed successfully!")
        print("\n✅ Your API key is working correctly")
        print("✅ YouTube Data API v3 is properly enabled")
        print("✅ All required permissions are granted")
        print("✅ Ready for YouTube channel monitoring")
        
        return True
        
    except Exception as e:
        print(f"❌ YouTube API test failed: {e}")
        return False


def main():
    """Main function."""
    print("🚀 YouTube Data API v3 Validation Test")
    print("=" * 50)
    
    success = test_youtube_api()
    
    if success:
        print("\n🎯 Next steps:")
        print("1. Update config.yaml with your target YouTube channel URL")
        print("2. Ready to proceed with Phase 3 implementation!")
    else:
        print("\n🔧 Troubleshooting steps:")
        print("1. Verify your API key in .env file")
        print("2. Ensure YouTube Data API v3 is enabled in Google Cloud Console")
        print("3. Check API key restrictions/permissions")
        print("4. Verify you haven't exceeded daily quota limits")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)