import os
import queue
import threading
import subprocess
import time
import re
from dataclasses import dataclass
from typing import Optional, Callable, Literal
from datetime import datetime, timedelta


JobMode = Literal["transcode", "remux"]


@dataclass
class TranscodeJob:
	source_path: str
	output_dir: str
	mode: JobMode = "transcode"
	title: Optional[str] = None
	uploader: Optional[str] = None
	upload_date: Optional[str] = None  # YYYYMMDD
	webpage_url: Optional[str] = None
	crf_quality: int = 23  # Default CRF quality
	on_complete: Optional[Callable[[str, bool], None]] = None


def _build_ffmpeg_transcode(src: str, dst: str, title: Optional[str], uploader: Optional[str], upload_date: Optional[str], webpage_url: Optional[str], crf_quality: int = 23) -> list[str]:
	cmd = [
		"ffmpeg",
		"-y",
		"-hide_banner",
		"-loglevel",
		"error",
		"-stats",
		"-i",
		src,
	]
	thumb_jpg = os.path.splitext(src)[0] + ".jpg"
	has_thumb = os.path.exists(thumb_jpg)
	if has_thumb:
		cmd += ["-i", thumb_jpg]
		cmd += ["-map", "0:v:0", "-map", "0:a:0?", "-map", "1:v:0"]
		cmd += [
			"-c:v:0", "libx264",
			"-crf", str(crf_quality),  # Use the CRF quality parameter
			"-preset", "medium",  # Changed from "slow" to "medium" for faster processing
			"-pix_fmt", "yuv420p",
			"-c:a:0", "aac",
			"-b:a:0", "160k",
			"-c:v:1", "mjpeg",
			"-disposition:v:1", "attached_pic",
			"-movflags", "+faststart",
		]
	else:
		cmd += ["-map", "0:v:0", "-map", "0:a:0?"]
		cmd += [
			"-c:v:0", "libx264",
			"-crf", str(crf_quality),  # Use the CRF quality parameter
			"-preset", "medium",  # Changed from "slow" to "medium"
			"-pix_fmt", "yuv420p",
			"-c:a:0", "aac",
			"-b:a:0", "160k",
			"-movflags", "+faststart",
		]
	# Metadata
	if title:
		cmd += ["-metadata", f"title={title}"]
	if uploader:
		cmd += ["-metadata", f"artist={uploader}", "-metadata", f"album_artist={uploader}", "-metadata", f"album={uploader}"]
	if upload_date and len(upload_date) == 8:
		date_fmt = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
		cmd += ["-metadata", f"date={date_fmt}", "-metadata", f"release_date={date_fmt}"]
	if webpage_url:
		cmd += ["-metadata", f"comment=Source: {webpage_url}"]
	cmd += [dst]
	return cmd


def _build_ffmpeg_remux(src: str, dst: str, title: Optional[str], uploader: Optional[str], upload_date: Optional[str], webpage_url: Optional[str]) -> list[str]:
	cmd = [
		"ffmpeg",
		"-y",
		"-hide_banner",
		"-loglevel",
		"error",
		"-stats",
		"-i",
		src,
	]
	thumb_jpg = os.path.splitext(src)[0] + ".jpg"
	has_thumb = os.path.exists(thumb_jpg)
	if has_thumb:
		cmd += ["-i", thumb_jpg]
		# Copy primary streams, encode cover art
		cmd += [
			"-map", "0:v:0", "-map", "0:a:0?", "-map", "1:v:0",
			"-c:v:0", "copy",
			"-c:a:0", "copy",
			"-c:v:1", "mjpeg",
			"-disposition:v:1", "attached_pic",
			"-movflags", "+faststart",
		]
	else:
		cmd += [
			"-map", "0:v:0", "-map", "0:a:0?",
			"-c:v:0", "copy",
			"-c:a:0", "copy",
			"-movflags", "+faststart",
		]
	# Metadata
	if title:
		cmd += ["-metadata", f"title={title}"]
	if uploader:
		cmd += ["-metadata", f"artist={uploader}", "-metadata", f"album_artist={uploader}", "-metadata", f"album={uploader}"]
	if upload_date and len(upload_date) == 8:
		date_fmt = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
		cmd += ["-metadata", f"date={date_fmt}", "-metadata", f"release_date={date_fmt}"]
	if webpage_url:
		cmd += ["-metadata", f"comment=Source: {webpage_url}"]
	cmd += [dst]
	return cmd


def _get_video_info(src: str) -> tuple[int, float]:
	"""Get video frame count and duration using ffprobe"""
	try:
		cmd = [
			"ffprobe", "-v", "quiet", "-select_streams", "v:0",
			"-show_entries", "stream=nb_frames:r_frame_rate:duration",
			"-of", "csv=p=0", src
		]
		result = subprocess.run(cmd, capture_output=True, text=True, check=True)
		output = result.stdout.strip()
		
		if output:
			parts = output.split(',')
			if len(parts) >= 3:
				frames = int(parts[0]) if parts[0].isdigit() else 0
				fps_str = parts[1] if len(parts) > 1 else "0"
				duration = float(parts[2]) if len(parts) > 2 and parts[2].replace('.', '').isdigit() else 0
				
				# Parse fps (e.g., "30000/1001" -> 29.97)
				if '/' in fps_str:
					num, den = map(int, fps_str.split('/'))
					fps = num / den if den > 0 else 30
				else:
					fps = float(fps_str) if fps_str.replace('.', '').isdigit() else 30
				
				# If frames not available, estimate from duration and fps
				if frames == 0 and duration > 0 and fps > 0:
					frames = int(duration * fps)
				
				return frames, fps
	except Exception:
		pass
	
	return 0, 30  # Default fallback


class ProgressBar:
	"""Beautiful CLI progress bar for transcoding"""
	
	def __init__(self, title: str, total_frames: int = 0):
		self.title = title
		self.total_frames = total_frames
		self.current_frame = 0
		self.start_time = time.time()
		self.last_update = 0
		self.fps = 0
		self.speed = 0
		self.eta = 0
	
	def update_from_ffmpeg_line(self, line: str):
		"""Parse FFmpeg output and update progress"""
		# Parse frame progress
		frame_match = re.search(r'frame=\s*(\d+)', line)
		if frame_match:
			self.current_frame = int(frame_match.group(1))
		
		# Parse FPS
		fps_match = re.search(r'fps=\s*(\d+)', line)
		if fps_match:
			self.fps = int(fps_match.group(1))
		
		# Parse speed
		speed_match = re.search(r'speed=\s*([\d.]+)x', line)
		if speed_match:
			self.speed = float(speed_match.group(1))
		
		# Parse time
		time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})', line)
		if time_match and self.fps > 0:
			hours, minutes, seconds = map(int, time_match.groups())
			elapsed = hours * 3600 + minutes * 60 + seconds
			if self.total_frames > 0:
				remaining_frames = self.total_frames - self.current_frame
				self.eta = remaining_frames / self.fps if self.fps > 0 else 0
	
	def render(self) -> str:
		"""Render the progress bar"""
		if self.total_frames == 0:
			return f"🔄 {self.title} | Frame: {self.current_frame:,} | FPS: {self.fps} | Speed: {self.speed:.1f}x"
		
		# Calculate progress percentage
		progress = min(1.0, self.current_frame / self.total_frames) if self.total_frames > 0 else 0
		bar_width = 30
		filled = int(bar_width * progress)
		bar = "█" * filled + "░" * (bar_width - filled)
		
		# Format ETA
		if self.eta > 0:
			eta_str = str(timedelta(seconds=int(self.eta)))
		else:
			eta_str = "??:??:??"
		
		# Format elapsed time
		elapsed = time.time() - self.start_time
		elapsed_str = str(timedelta(seconds=int(elapsed)))
		
		return f"🔄 {self.title} | {bar} | {progress*100:.1f}% | Frame: {self.current_frame:,}/{self.total_frames:,} | FPS: {self.fps} | Speed: {self.speed:.1f}x | Time: {elapsed_str} | ETA: {eta_str}"
	
	def clear(self):
		"""Clear the current line"""
		print("\r", end="", flush=True)
	
	def update(self):
		"""Update and display the progress bar"""
		now = time.time()
		if now - self.last_update >= 0.5:  # Update every 0.5 seconds
			self.clear()
			print(self.render(), end="", flush=True)
			self.last_update = now
	
	def finish(self, success: bool = True):
		"""Finish the progress bar"""
		self.clear()
		elapsed = time.time() - self.start_time
		elapsed_str = str(timedelta(seconds=int(elapsed)))
		
		if success:
			print(f"✅ {self.title} | Completed in {elapsed_str}")
		else:
			print(f"❌ {self.title} | Failed after {elapsed_str}")
		print()  # New line after completion


class TranscodeWorker(threading.Thread):
	def __init__(self, work_queue: "queue.Queue[TranscodeJob]", log_path: str):
		super().__init__(daemon=True)
		self.work_queue = work_queue
		self.log_path = log_path
		self._stop = threading.Event()

	def run(self) -> None:
		while not self._stop.is_set():
			try:
				job = self.work_queue.get(timeout=0.5)
			except queue.Empty:
				continue
			try:
				base = os.path.splitext(os.path.basename(job.source_path))[0]
				if job.mode == "remux" and job.source_path.lower().endswith(".mp4"):
					# For remuxing MP4s, use a temporary filename to avoid "Output same as Input" error
					dst = os.path.join(job.output_dir, f"{base}.tmp.mp4")
				else:
					dst = os.path.join(job.output_dir, f"{base}.mp4")
				if job.mode == "remux":
					cmd = _build_ffmpeg_remux(job.source_path, dst, job.title, job.uploader, job.upload_date, job.webpage_url)
				else:
					cmd = _build_ffmpeg_transcode(job.source_path, dst, job.title, job.uploader, job.upload_date, job.webpage_url, job.crf_quality)
				print(f"[transcode] Starting: {os.path.basename(job.source_path)} -> {os.path.basename(dst)} ({job.mode})")
				# Get video info for progress tracking
				total_frames, _ = _get_video_info(job.source_path)
				
				with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
					assert proc.stderr is not None
					progress_bar = ProgressBar(f"Transcoding {os.path.basename(job.source_path)}", total_frames)
					for line in proc.stderr:
						line = line.strip()
						if line:
							print(f"[transcode] {line}")
							progress_bar.update_from_ffmpeg_line(line)
							progress_bar.update()
					code = proc.wait()
					success = code == 0 and os.path.exists(dst)
					status = "OK" if success else "FAIL"
					progress_bar.finish(success)
					print(f"[transcode] Completed ({status}): {os.path.basename(job.source_path)} -> {os.path.basename(dst)}")
					if success:
						# Replace source if remux; cleanup intermediates
						try:
							if job.mode == "remux" and job.source_path.lower().endswith(".mp4"):
								# Replace original with the processed file
								os.replace(dst, job.source_path)
								dst = job.source_path
							else:
								os.remove(job.source_path)
						except Exception:
							pass
						thumb_jpg = os.path.splitext(job.source_path)[0] + ".jpg"
						if os.path.exists(thumb_jpg):
							try:
								os.remove(thumb_jpg)
							except Exception:
								pass
					self._append_log(f"{status}: {os.path.basename(job.source_path)} -> {os.path.basename(dst)}")
					if job.on_complete:
						job.on_complete(dst, success)
			except Exception as exc:
				self._append_log(f"ERROR: {job.source_path} | {exc}")
			finally:
				self.work_queue.task_done()

	def _append_log(self, text: str) -> None:
		with open(self.log_path, "a", encoding="utf-8") as f:
			f.write(text + "\n")

	def stop(self) -> None:
		self._stop.set() 