# ytFetcher

Arch Linux YouTube channel video downloader script.

## Quickstart

### Interactive Mode (Recommended for new users)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run_interactive.py
```

### Command Line Mode
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.main --channel-url "<CHANNEL_URL>" --downloader yt-dlp --output-path downloads/youtubeFetcher
```

## Features

- **Interactive CLI**: User-friendly prompts for all options
- **YouTube Support**: Download videos from channels, playlists, users, or individual videos
- **Date Filtering**: Download videos uploaded after a specific date
- **Keyword Filtering**: Download only videos with titles containing specific keywords
- **Single Video Support**: Download individual videos (filters are automatically skipped)
- **Quality Control**: Choose video quality with CRF settings (18-30, lower=higher quality)
- **Multiple Downloaders**: Support for yt-dlp (recommended) and youtube-dl
- **Automatic Transcoding**: Convert videos to MP4 with metadata
- **Retry Logic**: Configurable retry attempts for failed downloads 