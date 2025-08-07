#!/usr/bin/env python3
"""
Unit tests for season and episode parsing functionality.
"""

import unittest
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from download_manager import PlexNamingHelper
from youtube_client import YouTubeVideo


class TestSeasonParsing(unittest.TestCase):
    """Test cases for episode and season parsing."""
    
    def test_standard_formats(self):
        """Test standard SxxExx formats."""
        test_cases = [
            ("Game of Thrones S01E01", "Game of Thrones", 1, 1),
            ("Breaking Bad S3E7", "Breaking Bad", 3, 7),
            ("The Office S02E05", "The Office", 2, 5),
            ("The Mandalorian S03E05", "The Mandalorian", 3, 5),
            ("some program s03e05", "some program", 3, 5),  # Case insensitive
            ("PROGRAM S12E34", "PROGRAM", 12, 34),
        ]
        
        for title, expected_series, expected_season, expected_episode in test_cases:
            with self.subTest(title=title):
                series, season, episode = PlexNamingHelper.extract_episode_info(title)
                self.assertEqual(series, expected_series)
                self.assertEqual(season, expected_season)
                self.assertEqual(episode, expected_episode)
    
    def test_season_episode_spelled_out(self):
        """Test Season X Episode Y formats."""
        test_cases = [
            ("Doctor Who Season 12 Episode 4", "Doctor Who", 12, 4),
            ("Sherlock Season 4 Episode 1", "Sherlock", 4, 1),
        ]
        
        for title, expected_series, expected_season, expected_episode in test_cases:
            with self.subTest(title=title):
                series, season, episode = PlexNamingHelper.extract_episode_info(title)
                self.assertEqual(series, expected_series)
                self.assertEqual(season, expected_season)
                self.assertEqual(episode, expected_episode)
    
    def test_x_format(self):
        """Test 1x01 style formats."""
        test_cases = [
            ("Friends 1x01", "Friends", 1, 1),
            ("Lost 4x08", "Lost", 4, 8),
        ]
        
        for title, expected_series, expected_season, expected_episode in test_cases:
            with self.subTest(title=title):
                series, season, episode = PlexNamingHelper.extract_episode_info(title)
                self.assertEqual(series, expected_series)
                self.assertEqual(season, expected_season)
                self.assertEqual(episode, expected_episode)
    
    def test_series_episode_format(self):
        """Test 'Series X Episode Y' formats."""
        test_cases = [
            ("University Challenge Series 54 Episode 37", "University Challenge", 54, 37),
            ("Only Connect Series 21 Episode 3", "Only Connect", 21, 3),
        ]
        
        for title, expected_series, expected_season, expected_episode in test_cases:
            with self.subTest(title=title):
                series, season, episode = PlexNamingHelper.extract_episode_info(title)
                self.assertEqual(series, expected_series)
                self.assertEqual(season, expected_season)
                self.assertEqual(episode, expected_episode)
    
    def test_dash_separated_series(self):
        """Test dash-separated series formats."""
        test_cases = [
            ("Only Connect - Series 21 - Episode 3", "Only Connect", 21, 3),
            ("Taskmaster - Series 15 - Episode 2", "Taskmaster", 15, 2),
        ]
        
        for title, expected_series, expected_season, expected_episode in test_cases:
            with self.subTest(title=title):
                series, season, episode = PlexNamingHelper.extract_episode_info(title)
                self.assertEqual(series, expected_series)
                self.assertEqual(season, expected_season)
                self.assertEqual(episode, expected_episode)
    
    def test_episode_only_formats(self):
        """Test episode-only formats (default to Season 1)."""
        test_cases = [
            ("Some Show Episode 5", "Some Show", 1, 5),
            ("Random Program - Episode 12", "Random Program", 1, 12),
            ("QI - Series P - Episode 12", "QI - Series P", 1, 12),  # P isn't a number
        ]
        
        for title, expected_series, expected_season, expected_episode in test_cases:
            with self.subTest(title=title):
                series, season, episode = PlexNamingHelper.extract_episode_info(title)
                self.assertEqual(series, expected_series)
                self.assertEqual(season, expected_season)
                self.assertEqual(episode, expected_episode)
    
    def test_number_at_end(self):
        """Test titles with numbers at the end."""
        test_cases = [
            ("Daily Show 2024", "Daily Show", 1, 2024),
        ]
        
        for title, expected_series, expected_season, expected_episode in test_cases:
            with self.subTest(title=title):
                series, season, episode = PlexNamingHelper.extract_episode_info(title)
                self.assertEqual(series, expected_series)
                self.assertEqual(season, expected_season)
                self.assertEqual(episode, expected_episode)
    
    def test_no_match_fallback(self):
        """Test titles that don't match any pattern (should return None)."""
        test_cases = [
            "Random Video Title",
            "Just Some Content",
            "2024 Highlights",
            "Welcome to my channel",
        ]
        
        for title in test_cases:
            with self.subTest(title=title):
                series, season, episode = PlexNamingHelper.extract_episode_info(title)
                self.assertIsNone(series)
                self.assertIsNone(season)
                self.assertIsNone(episode)


class TestPlexPathGeneration(unittest.TestCase):
    """Test cases for Plex path generation."""
    
    def test_episode_path_generation(self):
        """Test path generation for detected episodes."""
        video = YouTubeVideo(
            "test", 
            "Only Connect - Series 21 - Episode 3", 
            "2024-08-04T22:21:00Z", 
            channel_title="Wheels on Genius"
        )
        
        output_dir, filename = PlexNamingHelper.generate_plex_path(video, "/tmp", True)
        
        expected_dir = "/tmp/Only Connect/Season 21"
        expected_filename = "Only Connect - S21E03 - Only Connect - Series 21 - Episode 3"
        
        self.assertEqual(output_dir, expected_dir)
        self.assertEqual(filename, expected_filename)
    
    def test_fallback_to_channel_name(self):
        """Test fallback to channel name for unmatched titles."""
        video = YouTubeVideo(
            "test", 
            "Random Video Title", 
            "2024-08-04T22:21:00Z", 
            channel_title="Test Channel"
        )
        
        output_dir, filename = PlexNamingHelper.generate_plex_path(video, "/tmp", True)
        
        expected_dir = "/tmp/Test Channel"
        expected_filename = "Random Video Title"
        
        self.assertEqual(output_dir, expected_dir)
        self.assertEqual(filename, expected_filename)
    
    def test_no_channel_name_fallback(self):
        """Test fallback when no channel name is provided."""
        video = YouTubeVideo(
            "test", 
            "Random Video Title", 
            "2024-08-04T22:21:00Z", 
            channel_title=""
        )
        
        output_dir, filename = PlexNamingHelper.generate_plex_path(video, "/tmp", True)
        
        expected_dir = "/tmp/Unknown Channel"
        expected_filename = "Random Video Title"
        
        self.assertEqual(output_dir, expected_dir)
        self.assertEqual(filename, expected_filename)
    
    def test_simple_organization(self):
        """Test simple organization (no season folders)."""
        video = YouTubeVideo(
            "test", 
            "Only Connect - Series 21 - Episode 3", 
            "2024-08-04T22:21:00Z", 
            channel_title="Wheels on Genius"
        )
        
        output_dir, filename = PlexNamingHelper.generate_plex_path(video, "/tmp", False)
        
        expected_dir = "/tmp/Only Connect"
        expected_filename = "Only Connect - Series 21 - Episode 3"
        
        self.assertEqual(output_dir, expected_dir)
        self.assertEqual(filename, expected_filename)


class TestFilenameSanitization(unittest.TestCase):
    """Test cases for filename sanitization."""
    
    def test_sanitize_basic(self):
        """Test basic filename sanitization."""
        test_cases = [
            ("Normal Title", "Normal Title"),
            ("Title/With/Slashes", "TitleWithSlashes"),
            ("Title:With:Colons", "TitleWithColons"),
            ("Title<With>Brackets", "TitleWithBrackets"),
            ("Title|With|Pipes", "TitleWithPipes"),
            ("Title?With?Questions", "TitleWithQuestions"),
            ("Title*With*Stars", "TitleWithStars"),
            ('Title"With"Quotes', "TitleWithQuotes"),
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = PlexNamingHelper.sanitize_filename(input_name)
                self.assertEqual(result, expected)
    
    def test_sanitize_long_filename(self):
        """Test truncation of very long filenames."""
        long_title = "A" * 300  # 300 characters
        result = PlexNamingHelper.sanitize_filename(long_title)
        
        self.assertLessEqual(len(result), 203)  # 200 + "..."
        self.assertTrue(result.endswith("..."))


if __name__ == '__main__':
    unittest.main()