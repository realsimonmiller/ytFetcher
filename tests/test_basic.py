"""
Basic tests for ytFetcher
"""

import pytest

from src.interactive_cli import InteractiveCLI
from src.processor import sort_videos


class TestInteractiveCLI:
    """Test InteractiveCLI functionality"""

    def test_url_validation(self):
        """Test YouTube URL validation"""
        cli = InteractiveCLI()

        # Valid URLs
        assert cli._validate_youtube_url("https://www.youtube.com/@ChannelName")
        assert cli._validate_youtube_url("https://www.youtube.com/@ChannelName/videos")
        assert cli._validate_youtube_url("https://www.youtube.com/watch?v=VIDEO_ID")
        assert cli._validate_youtube_url("https://youtu.be/VIDEO_ID")
        assert cli._validate_youtube_url("https://www.youtube.com/shorts/VIDEO_ID")

        # Invalid URLs
        assert not cli._validate_youtube_url("https://invalid.com")
        assert not cli._validate_youtube_url("not-a-url")
        assert not cli._validate_youtube_url("")

    def test_downloader_selection(self):
        """Test downloader selection logic"""
        cli = InteractiveCLI()

        # Test that the CLI has the expected downloader options
        # We can't test input() in unit tests, so we test the structure
        assert hasattr(cli, "_get_downloader")
        assert hasattr(cli, "downloader_options")

        # Test that the CLI has the expected downloader options
        expected_options = ["yt-dlp"]
        for option in expected_options:
            assert option in cli.downloader_options


class TestProcessor:
    """Test video processing functionality"""

    def test_sort_videos_keyword_filter(self):
        """Test keyword filtering"""
        videos = [
            {"title": "Steam Train Adventure", "upload_date": "20240101"},
            {"title": "Electric Train Review", "upload_date": "20230101"},
            {"title": "Steam Locomotive History", "upload_date": "20250101"},
            {"title": "Diesel Engine Guide", "upload_date": "20240101"},
        ]

        # Test keyword filter
        filtered = sort_videos(videos, keyword_filter="steam")
        assert len(filtered) == 2
        assert all("steam" in vid["title"].lower() for vid in filtered)

        # Test case insensitivity
        filtered = sort_videos(videos, keyword_filter="STEAM")
        assert len(filtered) == 2

    def test_sort_videos_date_filter(self):
        """Test date filtering"""
        videos = [
            {"title": "Video 1", "upload_date": "20240101"},
            {"title": "Video 2", "upload_date": "20230101"},
            {"title": "Video 3", "upload_date": "20250101"},
            {"title": "Video 4", "upload_date": "20240101"},
        ]

        # Test date filter
        filtered = sort_videos(videos, after_date="20240101")
        assert len(filtered) == 1
        assert filtered[0]["upload_date"] == "20250101"

    def test_sort_videos_no_filters(self):
        """Test sorting without filters"""
        videos = [
            {"title": "Video 1", "upload_date": "20240101"},
            {"title": "Video 2", "upload_date": "20230101"},
            {"title": "Video 3", "upload_date": "20250101"},
        ]

        # Test no filters
        filtered = sort_videos(videos)
        assert len(filtered) == 3

    def test_sort_videos_empty_list(self):
        """Test sorting empty video list"""
        videos = []
        filtered = sort_videos(videos)
        assert filtered == []

        filtered = sort_videos(videos, keyword_filter="test")
        assert filtered == []

        filtered = sort_videos(videos, after_date="20240101")
        assert filtered == []


if __name__ == "__main__":
    pytest.main([__file__])
