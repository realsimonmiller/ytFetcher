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
    video: Dict[str, Any], downloader: str, output_path: str, format_strategy: str, use_android: bool = False
) -> list[str]:
    url = video.get("webpage_url") or video.get("url") or video.get("id")
    if not url:
        raise DownloadError("Video has no URL or ID")
    
    output_template = f"{output_path}/%(title)s [%(id)s].%(ext)s"
    if downloader == "yt-dlp":
        cmd = [
            "yt-dlp",
            "-o",
            output_template,
            # Use the provided format strategy
            "-f",
            format_strategy,
            # Anti-detection measures
            "--user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
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
        
        # Try to add cookies if available, but don't fail if not
        try:
            import subprocess
            result = subprocess.run(["which", "google-chrome"], capture_output=True, text=True)
            if result.returncode == 0:
                cmd.extend(["--cookies-from-browser", "chrome"])
        except Exception:
            pass  # Skip cookies if Chrome not available
        
        # Add Android client if requested
        if use_android:
            cmd.extend(["--extractor-args", "youtube:player_client=android"])
        
        return cmd
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
        "bv*+ba/b",  # Best video + best audio, merged (most reliable)
        "best[height>=720]/best",  # Prefer 720p+ then best available
        "best[height>=480]/best",  # Prefer 480p+ then best available
        "best[height>=360]/best",  # Prefer 360p+ then best available
        "best",  # Just get the best available
    ]
    
    # Add Android client as a fallback strategy
    android_strategies = [
        "best",  # Android client with best available
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
    
    # If all regular strategies failed, try Android client as last resort
    print(f"    🔄 Trying Android client as last resort...")
    for android_strategy in android_strategies:
        command = _build_command_with_format(video, downloader, output_path, android_strategy, use_android=True)
        attempt = 0
        while attempt <= retries:
            print(f"    🔄 Trying Android client strategy: {android_strategy}")
            result = subprocess.run(command)
            if result.returncode == 0:
                path = _find_downloaded_file(output_path, video.get("id"))
                if path:
                    print(f"    ✅ Download successful with Android client!")
                    return path
            attempt += 1
            if attempt <= retries:
                time.sleep(2)
    
    print(f"    ❌ All download strategies failed for video")
    return None
