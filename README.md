# ytFetcher

[![CI/CD Pipeline](https://github.com/realsimonmiller/ytFetcher/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/realsimonmiller/ytFetcher/actions)
[![Code Quality](https://github.com/realsimonmiller/ytFetcher/workflows/Code%20Quality/badge.svg)](https://github.com/realsimonmiller/ytFetcher/actions)
[![Dependencies](https://github.com/realsimonmiller/ytFetcher/workflows/Dependencies/badge.svg)](https://github.com/realsimonmiller/ytFetcher/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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
- **CI/CD Pipeline**: Automated testing, linting, and quality checks
- **Code Quality**: Automated metrics and coverage reporting

## CI/CD Pipeline

This project includes a comprehensive GitHub Actions CI/CD pipeline:

### 🚀 **Automated Testing**
- **Linting**: Code formatting with Black, import sorting with isort
- **Style Check**: PEP 8 compliance with flake8
- **Type Checking**: Static type analysis with mypy
- **Multi-Python**: Tests run on Python 3.9, 3.10, 3.11, and 3.12

### 🔒 **Security & Quality**
- **Dependency Security**: Automated vulnerability scanning with safety
- **Code Coverage**: Test coverage reporting and analysis
- **Complexity Metrics**: Cyclomatic complexity and maintainability analysis
- **Quality Gates**: Automated PR reviews with quality metrics

### 📦 **Dependency Management**
- **Weekly Updates**: Automated dependency updates every Monday
- **Security Patches**: Automatic PR creation for security updates
- **Version Tracking**: Monitor outdated packages and dependencies

### 📊 **Quality Metrics**
- **Coverage Reports**: HTML and XML coverage reports
- **Complexity Analysis**: Radon-based code complexity metrics
- **PR Comments**: Automated quality reports on pull requests

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

The CI/CD pipeline will automatically run tests and provide quality feedback on your PR!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 