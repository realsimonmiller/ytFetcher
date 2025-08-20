import os
import re
from typing import Optional, Dict, Any
from datetime import datetime


class InteractiveCLI:
	"""Interactive CLI for YouTube channel video fetcher"""
	
	def __init__(self):
		self.options: Dict[str, Any] = {}
	
	def _validate_youtube_url(self, url: str) -> bool:
		"""Validate if the URL looks like a valid YouTube channel/playlist/video URL"""
		youtube_patterns = [
			r'https?://(?:www\.)?youtube\.com/@[\w-]+/?',  # Channel with or without /videos
			r'https?://(?:www\.)?youtube\.com/channel/[\w-]+',
			r'https?://(?:www\.)?youtube\.com/c/[\w-]+',
			r'https?://(?:www\.)?youtube\.com/user/[\w-]+',
			r'https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
			r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+&list=[\w-]+',
			r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',  # Single video (no playlist)
			r'https?://(?:www\.)?youtu\.be/[\w-]+',  # Shortened video URLs
			r'https?://(?:www\.)?youtube\.com/shorts/[\w-]+'  # YouTube Shorts
		]
		
		for pattern in youtube_patterns:
			if re.match(pattern, url):
				return True
		return False
	
	def _detect_url_type(self, url: str) -> str:
		"""Detect if URL is a single video, channel, or playlist"""
		# Single video patterns
		video_patterns = [
			r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+$',  # Single video (no playlist)
			r'https?://(?:www\.)?youtu\.be/[\w-]+',  # Shortened video URLs
			r'https?://(?:www\.)?youtube\.com/shorts/[\w-]+'  # YouTube Shorts
		]
		
		for pattern in video_patterns:
			if re.match(pattern, url):
				return "single_video"
		
		# Channel/playlist patterns
		channel_patterns = [
			r'https?://(?:www\.)?youtube\.com/@[\w-]+/videos?',
			r'https?://(?:www\.)?youtube\.com/channel/[\w-]+',
			r'https?://(?:www\.)?youtube\.com/c/[\w-]+',
			r'https?://(?:www\.)?youtube\.com/user/[\w-]+',
			r'https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
			r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+&list=[\w-]+'
		]
		
		for pattern in channel_patterns:
			if re.match(pattern, url):
				return "channel_or_playlist"
		
		return "unknown"
	
	def _validate_date_format(self, date_str: str) -> bool:
		"""Validate if the date string is in YYYYMMDD format"""
		if not date_str:
			return True
		
		try:
			datetime.strptime(date_str, "%Y%m%d")
			return True
		except ValueError:
			return False
	
	def _validate_directory(self, path: str) -> bool:
		"""Validate if the directory path is valid and writable"""
		try:
			# Check if parent directory exists and is writable
			parent_dir = os.path.dirname(os.path.abspath(path))
			if not os.path.exists(parent_dir):
				return os.access(os.path.dirname(parent_dir), os.W_OK)
			return os.access(parent_dir, os.W_OK)
		except Exception:
			return False
	
	def _get_channel_url(self) -> str:
		"""Prompt for YouTube URL (channel, playlist, or single video)"""
		print("\n" + "="*60)
		print("🎥 YouTube Video Fetcher")
		print("="*60)
		
		while True:
			url = input("\n📺 Enter YouTube URL (channel, playlist, or single video): ").strip()
			
			if not url:
				print("❌ URL cannot be empty. Please try again.")
				continue
			
			if not self._validate_youtube_url(url):
				print("❌ Invalid YouTube URL format. Please enter a valid URL.")
				print("   Examples:")
				print("   - Channel: https://www.youtube.com/@ChannelName or https://www.youtube.com/@ChannelName/videos")
				print("   - Playlist: https://www.youtube.com/playlist?list=PLAYLIST_ID")
				print("   - Single Video: https://www.youtube.com/watch?v=VIDEO_ID")
				print("   - Short URL: https://youtu.be/VIDEO_ID")
				continue
			
			# Detect URL type and provide feedback
			url_type = self._detect_url_type(url)
			if url_type == "single_video":
				print(f"✅ Single video detected: {url}")
				print("   📝 Note: Date and keyword filters will be ignored for single videos")
			elif url_type == "channel_or_playlist":
				print(f"✅ Channel/playlist detected: {url}")
			else:
				print(f"✅ YouTube URL detected: {url}")
			
			return url
	
	def _get_downloader(self) -> str:
		"""Get downloader selection from user"""
		print("----------------------------------------")
		print("📥 Downloader Selection")
		print("----------------------------------------")
		print("Available downloaders:")
		print("1. yt-dlp (recommended - faster, more features)")
		print("2. youtube-dl (currently broken - not recommended)")
		print()
		print("Note: youtube-dl is outdated and may fail to download videos.")
		print("yt-dlp is strongly recommended for reliable downloads.")
		print()
		
		while True:
			choice = input("Select downloader (1 or 2) [default: 1]: ").strip()
			if not choice:
				return "yt-dlp"
			if choice == "1":
				return "yt-dlp"
			elif choice == "2":
				print("⚠️  Warning: youtube-dl is outdated and may fail!")
				confirm = input("Are you sure you want to use youtube-dl? (y/n): ").strip().lower()
				if confirm in ["y", "yes"]:
					return "youtube-dl"
				else:
					print("✅ Defaulting to yt-dlp")
					return "yt-dlp"
			else:
				print("❌ Invalid choice. Please enter 1 or 2.")
	
	def _get_after_date(self) -> Optional[str]:
		"""Prompt for after date filter"""
		print("\n" + "-"*40)
		print("📅 Date Filter")
		print("-"*40)
		print("Only download videos uploaded after a specific date.")
		print("Leave empty to download all videos.")
		print("Format: YYYYMMDD (e.g., 20240101 for January 1, 2024)")
		
		while True:
			date_input = input("\nEnter after date (YYYYMMDD) or press Enter to skip: ").strip()
			
			if not date_input:
				print("✅ No date filter applied - will download all videos")
				return None
			
			if not self._validate_date_format(date_input):
				print("❌ Invalid date format. Please use YYYYMMDD format.")
				continue
			
			# Convert to readable format for confirmation
			try:
				parsed_date = datetime.strptime(date_input, "%Y%m%d")
				readable_date = parsed_date.strftime("%B %d, %Y")
				print(f"✅ Date filter set to: {readable_date}")
				return date_input
			except ValueError:
				print("❌ Invalid date. Please try again.")
	
	def _get_keyword_filter(self) -> Optional[str]:
		"""Prompt for keyword filter"""
		print("\n" + "-"*40)
		print("🔍 Keyword Filter")
		print("-"*40)
		print("Only download videos with titles containing specific keywords.")
		print("Leave empty to download all videos.")
		print("Example: 'steam trains' will only download videos with 'steam trains' in the title")
		print("Note: Search is case-insensitive")
		
		while True:
			keyword_input = input("\nEnter keyword filter or press Enter to skip: ").strip()
			
			if not keyword_input:
				print("✅ No keyword filter applied - will download all videos")
				return None
			
			if len(keyword_input) < 2:
				print("❌ Keyword must be at least 2 characters long.")
				continue
			
			if len(keyword_input) > 100:
				print("❌ Keyword is too long. Please keep it under 100 characters.")
				continue
			
			print(f"✅ Keyword filter set to: '{keyword_input}'")
			return keyword_input
	
	def _get_crf_quality(self) -> int:
		"""Prompt for CRF quality setting"""
		print("\n" + "-"*40)
		print("🎬 Video Quality Settings")
		print("-"*40)
		print("CRF (Constant Rate Factor) controls video quality and file size.")
		print("Lower numbers = higher quality, larger files, slower processing")
		print("Higher numbers = lower quality, smaller files, faster processing")
		print()
		print("Quality Options (for a 20-minute 1080p video):")
		print("1. CRF 18 (Visually Lossless) - ~2.5GB, ~45 min processing")
		print("2. CRF 20 (Very High)        - ~2.0GB, ~35 min processing")
		print("3. CRF 23 (High)             - ~1.5GB, ~25 min processing  ← RECOMMENDED")
		print("4. CRF 26 (Good)             - ~1.2GB, ~20 min processing")
		print("5. CRF 28 (Standard)         - ~1.0GB, ~15 min processing")
		print("6. CRF 30 (Acceptable)       - ~0.8GB, ~12 min processing")
		print()
		print("Note: Processing times are estimates. Actual times depend on your hardware.")
		
		while True:
			choice = input("\nSelect quality level (1-6) [default: 3]: ").strip()
			
			if not choice:
				return 23
			
			crf_map = {
				"1": 18,
				"2": 20,
				"3": 23,
				"4": 26,
				"5": 28,
				"6": 30
			}
			
			if choice in crf_map:
				crf_value = crf_map[choice]
				quality_desc = {
					18: "Visually Lossless",
					20: "Very High",
					23: "High (Recommended)",
					26: "Good",
					28: "Standard",
					30: "Acceptable"
				}[crf_value]
				
				print(f"✅ Quality set to: CRF {crf_value} ({quality_desc})")
				return crf_value
			else:
				print("❌ Invalid choice. Please enter 1-6.")
	
	def _get_output_path(self) -> str:
		"""Prompt for output directory"""
		print("\n" + "-"*40)
		print("📁 Output Directory")
		print("-"*40)
		print("Where should videos be downloaded?")
		print("The program will create subdirectories as needed.")
		
		default_path = "downloads/youtubeFetcher"
		
		while True:
			path_input = input(f"\nEnter output path [default: {default_path}]: ").strip()
			
			if not path_input:
				path_input = default_path
			
			if not self._validate_directory(path_input):
				print("❌ Invalid directory path or insufficient permissions.")
				print("   Please enter a valid, writable directory path.")
				continue
			
			print(f"✅ Output directory: {path_input}")
			return path_input
	
	def _get_max_retries(self) -> int:
		"""Prompt for maximum download retries"""
		print("\n" + "-"*40)
		print("🔄 Download Retries")
		print("-"*40)
		print("How many times should the program retry failed downloads?")
		
		while True:
			retries_input = input("\nEnter max retries [default: 3]: ").strip()
			
			if not retries_input:
				return 3
			
			try:
				retries = int(retries_input)
				if retries < 0 or retries > 10:
					print("❌ Please enter a number between 0 and 10.")
					continue
				
				print(f"✅ Max retries set to: {retries}")
				return retries
			except ValueError:
				print("❌ Please enter a valid number.")
	
	def _confirm_settings(self) -> bool:
		"""Show summary and confirm settings"""
		print("\n" + "="*60)
		print("📋 Settings Summary")
		print("="*60)
		url_type = self._detect_url_type(self.options['channel_url'])
		is_single_video = url_type == "single_video"
		
		print(f"Channel URL: {self.options['channel_url']}")
		print(f"URL Type: {'Single Video' if is_single_video else 'Channel/Playlist'}")
		print(f"Downloader: {self.options['downloader']}")
		
		if is_single_video:
			print(f"After Date: Skipped (single video)")
			print(f"Keyword Filter: Skipped (single video)")
		else:
			print(f"After Date: {self.options['after_date'] or 'All videos'}")
			print(f"Keyword Filter: {self.options['keyword_filter'] or 'All videos'}")
		
		print(f"Video Quality: CRF {self.options['crf_quality']}")
		print(f"Output Path: {self.options['output_path']}")
		print(f"Max Retries: {self.options['max_retries']}")
		
		while True:
			confirm = input("\nProceed with these settings? (y/n): ").strip().lower()
			
			if confirm in ['y', 'yes']:
				return True
			elif confirm in ['n', 'no']:
				return False
			else:
				print("❌ Please enter 'y' or 'n'.")
	
	def run(self) -> Dict[str, Any]:
		"""Run the interactive CLI and return the collected options"""
		try:
			# Collect all options
			self.options['channel_url'] = self._get_channel_url()
			self.options['downloader'] = self._get_downloader()
			
			# Check if this is a single video
			url_type = self._detect_url_type(self.options['channel_url'])
			is_single_video = url_type == "single_video"
			
			if is_single_video:
				# Skip filters for single videos
				self.options['after_date'] = None
				self.options['keyword_filter'] = None
				print("\n📝 Single video detected - skipping date and keyword filters")
			else:
				# Show filters for channels/playlists
				self.options['after_date'] = self._get_after_date()
				self.options['keyword_filter'] = self._get_keyword_filter()
			
			self.options['crf_quality'] = self._get_crf_quality()
			self.options['output_path'] = self._get_output_path()
			self.options['max_retries'] = self._get_max_retries()
			
			# Confirm settings
			if self._confirm_settings():
				print("\n🚀 Starting YouTube video fetcher...")
				return self.options
			else:
				print("\n❌ Setup cancelled by user.")
				return {}
				
		except KeyboardInterrupt:
			print("\n\n❌ Setup interrupted by user.")
			return {}
		except Exception as e:
			print(f"\n❌ An error occurred: {e}")
			return {}


def run_interactive_cli() -> Dict[str, Any]:
	"""Convenience function to run the interactive CLI"""
	cli = InteractiveCLI()
	return cli.run() 