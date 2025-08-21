from typing import Any, Dict, List, Optional


def get_videos(url: str) -> List[Dict[str, Any]]:
    """Return a list of videos with id, title, upload_date, uploader, and webpage_url.

    This function handles both single videos and channels/playlists.
    For single videos, it returns a list with one video.
    For channels/playlists, it returns all videos.
    """
    try:
        import yt_dlp as ytdlp

        # Detect if this is a single video or channel/playlist
        ydl_opts = {"quiet": True, "extract_flat": "in_playlist"}
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        # Provide helpful error message
        error_msg = f"Failed to fetch video list: {exc}"
        if "yt initial data" in str(exc):
            error_msg += "\n\nThis usually means yt-dlp is outdated and can't handle modern YouTube."
            error_msg += "\nPlease ensure yt-dlp is properly installed: pip install --upgrade yt-dlp"
        raise RuntimeError(error_msg)

    # Check if this is a single video (no entries list)
    if not isinstance(info, dict):
        return []

    entries = info.get("entries", [])

    # If no entries, this might be a single video
    if not entries:
        # Check if it's a single video
        if info.get("_type") == "video" or "id" in info:
            # Convert single video to list format
            vid = {
                "id": info.get("id"),
                "title": info.get("title"),
                "upload_date": info.get("upload_date"),
                "uploader": info.get("uploader") or info.get("channel"),
                "webpage_url": info.get("webpage_url") or url,
            }
            return [vid]
        return []

    # Process channel/playlist entries
    videos: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        vid = {
            "id": entry.get("id"),
            "title": entry.get("title"),
            "upload_date": entry.get("upload_date"),
            "uploader": entry.get("uploader") or entry.get("channel"),
            "webpage_url": entry.get("url") or entry.get("webpage_url"),
        }
        videos.append(vid)
    return videos


def get_video_metadata_by_id(video_id: str) -> Optional[Dict[str, Any]]:
    """Fetch metadata for a single YouTube video id using yt_dlp.
    Returns dict with title, uploader, upload_date, webpage_url.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        import yt_dlp as ytdlp

        ydl_opts = {"quiet": True}
        with ytdlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return None
    if not isinstance(info, dict):
        return None
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
        "upload_date": info.get("upload_date"),
        "webpage_url": info.get("webpage_url") or url,
    }
