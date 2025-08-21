from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    # Expecting YYYYMMDD from yt_dlp
    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except Exception:
        return None


def sort_videos(
    videos: List[Dict[str, Any]],
    after_date: Optional[str] = None,
    keyword_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    threshold = _parse_date(after_date)
    filtered: List[Dict[str, Any]] = []

    for v in videos:
        # Apply date filter
        ud = _parse_date(v.get("upload_date"))
        if threshold is not None and ud is not None and ud <= threshold:
            continue

        # Apply keyword filter
        if keyword_filter:
            title = v.get("title", "").lower()
            if keyword_filter.lower() not in title:
                continue

        filtered.append(v)

    return sorted(
        filtered,
        key=lambda v: (_parse_date(v.get("upload_date")) or datetime.min),
        reverse=True,
    )
