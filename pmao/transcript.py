import re
from pathlib import Path


def preprocess_vtt(text: str) -> str:
    """Convert WebVTT to plain 'Name: text' lines."""
    lines = []
    current_speaker = None
    current_text = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line == "WEBVTT":
            if current_speaker and current_text:
                lines.append(f"{current_speaker}: {' '.join(current_text)}")
                current_text = []
            continue
        if "-->" in line:
            continue
        speaker_match = re.match(r"<v ([^>]+)>(.*)", line)
        if speaker_match:
            if current_speaker and current_text:
                lines.append(f"{current_speaker}: {' '.join(current_text)}")
                current_text = []
            current_speaker = speaker_match.group(1).strip()
            rest = speaker_match.group(2).strip().replace("</v>", "").strip()
            if rest:
                current_text.append(rest)
            continue
        if current_speaker:
            current_text.append(line)

    if current_speaker and current_text:
        lines.append(f"{current_speaker}: {' '.join(current_text)}")

    return "\n".join(lines)


def preprocess_transcript(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".vtt":
        return preprocess_vtt(text)
    return text
