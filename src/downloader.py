import os
import subprocess
import time
from typing import Any, Dict, Optional


class DownloadError(Exception):
    pass


def _build_command(
    video: Dict[str, Any], downloader: str, output_path: str
) -> list[str]:
    url = video.get("webpage_url") or video.get("url") or video.get("id")
    if not url:
        raise DownloadError("Video has no URL or ID")
    # Prefer >=720p; allow separate video+audio with fallback to best single file
    # We'll tag/transcode in background if needed
    format_selector = "bv*+ba/b"
    output_template = f"{output_path}/%(title)s [%(id)s].%(ext)s"
    if downloader == "yt-dlp":
        return [
            "yt-dlp",
            "-o",
            output_template,
            "-S",
            "res:2160,res:1440,res:1080,res:720,codec:avc1,ext:mp4",
            "-f",
            format_selector,
            "--write-thumbnail",
            "--convert-thumbnails",
            "jpg",
            "--progress",
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
    command = _build_command(video, downloader, output_path)
    attempt = 0
    while attempt <= retries:
        # Inherit stdout/stderr so the user can see native progress output
        result = subprocess.run(command)
        if result.returncode == 0:
            # Try to find the downloaded file by id
            path = _find_downloaded_file(output_path, video.get("id"))
            return path
        attempt += 1
        if attempt <= retries:
            time.sleep(1)
    return None
