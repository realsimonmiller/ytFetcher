from typing import Set


def load_downloaded_ids(log_path: str) -> Set[str]:
	ids: Set[str] = set()
	try:
		with open(log_path, "r", encoding="utf-8") as f:
			for line in f:
				line = line.strip()
				if line:
					ids.add(line)
	except FileNotFoundError:
		return set()
	return ids


def append_line(path: str, text: str) -> None:
	with open(path, "a", encoding="utf-8") as f:
		f.write(text + "\n") 