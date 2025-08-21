import os
import subprocess
import time
from typing import Any, Dict, Optional


class DownloadError(Exception):
    pass


def _build_command(
    video: Dict[str, Any], downloader: str, output_path: str
) -> list[str]:
    """Build command with default format strategy"""
    return _build_command_with_format(video, downloader, output_path, "best[height>=720]/best")


def _build_command_with_format(
    video: Dict[str, Any], downloader: str, output_path: str, format_strategy: str
) -> list[str]:
    url = video.get("webpage_url") or video.get("url") or video.get("id")
    if not url:
        raise DownloadError("Video has no URL or ID")
    
    output_template = f"{output_path}/%(title)s [%(id)s].%(ext)s"
    if downloader == "yt-dlp":
        return [
            "yt-dlp",
            "-o",
            output_template,
            # Use the provided format strategy
            "-f",
            format_strategy,
            # Anti-detection measures
            "--user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "--cookies-from-browser",
            "chrome",
            # Thumbnail handling
            "--write-thumbnail",
            "--convert-thumbnails",
            "jpg",
            # Progress and retry
            "--progress",
            "--retries",
            "3",
            "--fragment-retries",
            "3",
            url,
        ]
    else:
        raise DownloadError(f"Unsupported downloader: {downloader}")


def _find_downloaded_file(output_path: str, video_id: Optional[str]) -> Optional[str]:
    if not video_id:
        return None
    pattern_1 = f" [{video_id}]."
    candidates = []
    for name in os.listdir(output_path):
        if pattern_1 in name:
            full = os.path.join(output_path, name)
            if os.path.isfile(full):
                candidates.append(full)
    if not candidates:
        return None
    # Return the most recently modified candidate
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def download_video(
    video: Dict[str, Any], downloader: str, output_path: str, retries: int = 3
) -> Optional[str]:
    url = video.get("webpage_url") or video.get("url") or video.get("id")
    if not url:
        return None
    
    # Try different format strategies if the first one fails
    format_strategies = [
        "best[height>=720]/best",  # Prefer 720p+ then best available
        "best",  # Just get the best available
        "best[height>=480]/best",  # Prefer 480p+ then best available
        "best[height>=360]/best",  # Prefer 360p+ then best available
        "best",  # Just get the best available
    ]
    
    for strategy_index, format_strategy in enumerate(format_strategies):
        command = _build_command_with_format(video, downloader, output_path, format_strategy)
        attempt = 0
        while attempt <= retries:
            print(f"    🔄 Trying format strategy {strategy_index + 1}/{len(format_strategies)}: {format_strategy}")
            # Inherit stdout/stderr so the user can see native progress output
            result = subprocess.run(command)
            if result.returncode == 0:
                # Try to find the downloaded file by id
                path = _find_downloaded_file(output_path, video.get("id"))
                if path:
                    print(f"    ✅ Download successful with strategy: {format_strategy}")
                    return path
            attempt += 1
            if attempt <= retries:
                time.sleep(2)  # Longer delay between retries
        
        if strategy_index < len(format_strategies) - 1:
            print(f"    ⚠️  Strategy {format_strategy} failed, trying next...")
            time.sleep(3)  # Delay between strategies
    
    print(f"    ❌ All download strategies failed for video")
    return None
