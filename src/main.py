import argparse
import os
import re
from typing import Any, Dict, List

from src.config import (DOWNLOADER_DEFAULT, MAX_RETRIES_DEFAULT,
                        OUTPUT_DIR_DEFAULT)
from src.downloader import download_video
from src.fetcher import get_video_metadata_by_id, get_videos
from src.interactive_cli import run_interactive_cli
from src.logging_util import append_line, load_downloaded_ids
from src.processor import sort_videos
from src.transcoder import TranscodeJob, TranscodeWorker


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _extract_id_from_filename(filename: str) -> str:
    m = re.search(r"\[([A-Za-z0-9_-]{8,})\]", filename)
    return m.group(1) if m else ""


def backfill_existing_media(
    output_dir: str, queue_ref, counters: Dict[str, int], crf_quality: int
) -> None:
    # Remove partials
    for name in os.listdir(output_dir):
        if name.endswith(".part") or name.endswith(".ytdl"):
            try:
                os.remove(os.path.join(output_dir, name))
            except Exception:
                pass
    # Queue .webm for transcode and .mp4 with adjacent .jpg for remux
    for name in os.listdir(output_dir):
        full = os.path.join(output_dir, name)
        if not os.path.isfile(full):
            continue
        base, ext = os.path.splitext(name)
        if ext.lower() == ".webm":
            video_id = _extract_id_from_filename(name) or None
            meta = get_video_metadata_by_id(video_id) if video_id else None
            queue_ref.put(
                TranscodeJob(
                    source_path=full,
                    output_dir=output_dir,
                    mode="transcode",
                    title=(meta or {}).get("title"),
                    uploader=(meta or {}).get("uploader"),
                    upload_date=(meta or {}).get("upload_date"),
                    webpage_url=(meta or {}).get("webpage_url"),
                    crf_quality=crf_quality,
                )
            )
            counters["queued"] += 1
        elif ext.lower() == ".mp4":
            thumb = os.path.join(output_dir, base + ".jpg")
            if os.path.exists(thumb):
                # Check if the MP4 already has proper metadata by trying to read it
                needs_processing = True
                try:
                    import subprocess

                    result = subprocess.run(
                        [
                            "ffprobe",
                            "-v",
                            "quiet",
                            "-print_format",
                            "json",
                            "-show_format",
                            full,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if result.returncode == 0 and result.stdout:
                        # Check if it has title metadata
                        if '"title"' in result.stdout and '"artist"' in result.stdout:
                            # File already has metadata, skip it
                            print(f"    ⏭️  Skipping {name} - already has metadata")
                            needs_processing = False
                except Exception as e:
                    # If we can't check, assume it needs processing
                    print(f"    ⚠️  Could not check metadata for {name}: {e}")
                    needs_processing = True

                if needs_processing:
                    video_id = _extract_id_from_filename(name) or None
                    meta = get_video_metadata_by_id(video_id) if video_id else None
                    queue_ref.put(
                        TranscodeJob(
                            source_path=full,
                            output_dir=output_dir,
                            mode="remux",
                            title=(meta or {}).get("title"),
                            uploader=(meta or {}).get("uploader"),
                            upload_date=(meta or {}).get("upload_date"),
                            webpage_url=(meta or {}).get("webpage_url"),
                            crf_quality=crf_quality,
                        )
                    )
                    counters["queued"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube channel video fetcher")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument(
        "--channel-url", help="Channel or playlist URL (required unless --interactive)"
    )
    parser.add_argument(
        "--downloader",
        default=DOWNLOADER_DEFAULT,
        choices=["yt-dlp"],
        help="Downloader to use (yt-dlp only)",
    )
    parser.add_argument(
        "--after-date", default=None, help="Only include videos after YYYYMMDD"
    )
    parser.add_argument(
        "--keyword-filter",
        default=None,
        help="Only include videos with title containing this keyword",
    )
    parser.add_argument(
        "--crf-quality",
        type=int,
        default=23,
        help="Video quality CRF value (18-30, lower=higher quality)",
    )
    parser.add_argument(
        "--output-path", default=OUTPUT_DIR_DEFAULT, help="Output directory base"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=MAX_RETRIES_DEFAULT,
        help="Maximum download retries",
    )
    args = parser.parse_args()

    # Handle interactive mode
    if args.interactive:
        interactive_options = run_interactive_cli()
        if not interactive_options:
            print("❌ Interactive setup was cancelled or failed. Exiting.")
            return

        # Update args with interactive choices
        args.channel_url = interactive_options["channel_url"]
        args.downloader = interactive_options["downloader"]
        args.after_date = interactive_options["after_date"]
        args.keyword_filter = interactive_options["keyword_filter"]
        args.crf_quality = interactive_options["crf_quality"]
        args.output_path = interactive_options["output_path"]
        args.max_retries = interactive_options["max_retries"]
    elif not args.channel_url:
        parser.error("--channel-url is required unless --interactive is specified")

    print(f"[0/7] Output directory: {args.output_path}")
    ensure_dir(args.output_path)

    # Create log files in the output directory
    download_log = os.path.join(args.output_path, "downloaded_videos.log")
    error_log = os.path.join(args.output_path, "errors.log")
    open(download_log, "a", encoding="utf-8").close()
    open(error_log, "a", encoding="utf-8").close()
    print(f"[0/7] Download log: {download_log} | Error log: {error_log}")

    # Background transcode setup
    transcode_log = os.path.join(args.output_path, "transcode.log")
    open(transcode_log, "a", encoding="utf-8").close()
    transcode_queue: "queue.Queue[TranscodeJob]"
    import queue

    transcode_queue = queue.Queue()
    worker = TranscodeWorker(transcode_queue, transcode_log)
    worker.start()
    print(f"[0/7] Background transcoder started; log -> {transcode_log}")
    print(
        f"[0/7] Transcoding: CRF {args.crf_quality} (quality), Medium preset (balanced speed)"
    )

    # Backfill cleanup for existing files
    counters = {"queued": 0}
    backfill_existing_media(
        args.output_path, transcode_queue, counters, args.crf_quality
    )
    if counters["queued"]:
        print(f"[1/7] Backfill queued: {counters['queued']} items for cleanup/metadata")
    else:
        print("[1/7] Backfill: nothing to process")

    print(f"[2/7] Fetching videos from: {args.channel_url}")
    videos: List[Dict[str, Any]] = get_videos(args.channel_url)
    print(f"[2/7] Found {len(videos)} entries (pre-filter)")

    # Check if this is a single video
    is_single_video = len(videos) == 1 and "watch" in args.channel_url

    filter_info = []
    if is_single_video:
        print("[3/7] Single video detected - skipping filters")
        filter_str = "None (single video)"
    else:
        if args.after_date:
            filter_info.append(f"after_date={args.after_date}")
        if args.keyword_filter:
            filter_info.append(f"keyword='{args.keyword_filter}'")

        filter_str = ", ".join(filter_info) if filter_info else "None"
        print(f"[3/7] Applying sort/filter ({filter_str})")
        videos = sort_videos(
            videos, after_date=args.after_date, keyword_filter=args.keyword_filter
        )
        print(f"[3/7] {len(videos)} videos after filter")

    print("[4/7] Checking previously downloaded IDs")
    downloaded_ids = load_downloaded_ids(download_log)
    print(f"[4/7] {len(downloaded_ids)} IDs already downloaded")

    successes = 0
    failures = 0
    queued_transcodes = counters["queued"]
    total = len(videos)
    for index, v in enumerate(videos, start=1):
        title = v.get("title") or "<no-title>"
        uploader = v.get("uploader") or None
        upload_date = v.get("upload_date") or None
        webpage_url = v.get("webpage_url") or None
        video_id = v.get("id") or "<no-id>"
        if video_id in downloaded_ids:
            print(
                f"({index}/{total}) Skipping already downloaded: {title} [{video_id}]"
            )
            continue

        channel_dir = args.output_path
        ensure_dir(channel_dir)
        print(
            f"({index}/{total}) Downloading: {title} [{video_id}] via {args.downloader} -> {channel_dir}"
        )
        path = download_video(v, args.downloader, channel_dir, retries=args.max_retries)
        if path:
            print(f"    ✓ Downloaded: {os.path.basename(path)}")
            if path.lower().endswith(".mp4"):
                transcode_queue.put(
                    TranscodeJob(
                        source_path=path,
                        output_dir=channel_dir,
                        mode="remux",
                        title=title,
                        uploader=uploader,
                        upload_date=upload_date,
                        webpage_url=webpage_url,
                        crf_quality=args.crf_quality,
                    )
                )
                queued_transcodes += 1
                print(f"    ↳ queued for remux metadata: {os.path.basename(path)}")
            else:
                transcode_queue.put(
                    TranscodeJob(
                        source_path=path,
                        output_dir=channel_dir,
                        mode="transcode",
                        title=title,
                        uploader=uploader,
                        upload_date=upload_date,
                        webpage_url=webpage_url,
                        crf_quality=args.crf_quality,
                    )
                )
                queued_transcodes += 1
                print(f"    ↳ queued for transcode: {os.path.basename(path)} -> .mp4")
            if video_id != "<no-id>":
                append_line(download_log, video_id)
                successes += 1
        else:
            print(f"    ✗ Download failed: {title}")
            append_line(error_log, f"Failed: {video_id or title}")
            failures += 1

    print(f"[5/7] All downloads attempted. Queued post-process: {queued_transcodes}")
    print(
        "[6/7] Waiting for background post-processing to finish (see transcode.log for details)..."
    )
    transcode_queue.join()
    worker.stop()
    print("[6/7] Post-processing completed.")

    print(
        f"[7/7] Summary: Successes={successes}, Failures={failures}, PostProcessed={queued_transcodes}"
    )
    try:
        import subprocess  # local import to avoid global dependency

        subprocess.run(
            [
                "notify-send",
                "YouTube Downloader",
                f"Done. Success: {successes}, Failures: {failures}",
            ],
            check=False,
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
