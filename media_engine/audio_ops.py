import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError


AUDIO_MIME_BY_EXTENSION = {
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "opus": "audio/ogg",
    "webm": "audio/webm",
}
AUDIO_EXTENSIONS = frozenset(AUDIO_MIME_BY_EXTENSION)


def require_binary(name):
    path = shutil.which(name)
    if not path:
        raise ValidationError(
            f"{name} is required for Media Engine audio processing."
        )
    return path


def probe_audio_bytes(raw, *, suffix=".mp3"):
    ffprobe = require_binary("ffprobe")
    with tempfile.NamedTemporaryFile(suffix=suffix) as source:
        source.write(raw)
        source.flush()
        proc = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries",
                "format=duration,bit_rate,format_name:"
                "stream=codec_type,codec_name,sample_rate,channels",
                "-of", "json",
                source.name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=20,
        )
    if proc.returncode:
        raise ValidationError("Invalid or unsupported audio file.")
    try:
        payload = json.loads(proc.stdout.decode("utf-8", errors="replace") or "{}")
        streams = [
            item for item in payload.get("streams", [])
            if item.get("codec_type") == "audio"
        ]
        if not streams:
            raise ValueError("missing audio stream")
        stream = streams[0]
        fmt = payload.get("format") or {}
        duration = float(fmt.get("duration") or 0)
        if duration <= 0:
            raise ValueError("invalid duration")
        return {
            "duration_ms": int(round(duration * 1000)),
            "bit_rate": int(fmt.get("bit_rate") or 0),
            "format_name": str(fmt.get("format_name") or ""),
            "codec_name": str(stream.get("codec_name") or ""),
            "sample_rate": int(stream.get("sample_rate") or 0),
            "channels": int(stream.get("channels") or 0),
        }
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValidationError("Invalid or unsupported audio metadata.") from exc


def transcode_audio_bytes(raw, *, source_suffix=".mp3", profile=None):
    profile = profile or {}
    ffmpeg = require_binary("ffmpeg")
    bitrate = max(48, min(int(profile.get("bitrate_kbps") or 96), 192))
    sample_rate = max(22050, min(int(profile.get("sample_rate") or 44100), 48000))
    channels = 1 if int(profile.get("channels") or 2) == 1 else 2
    output_format = str(profile.get("fallback_format") or "mp3").lower()
    if output_format != "mp3":
        raise ValidationError("The standard audio processor currently emits MP3 only.")

    with tempfile.TemporaryDirectory(prefix="moe-audio-") as tmp:
        source = Path(tmp) / f"source{source_suffix}"
        target = Path(tmp) / "optimized.mp3"
        source.write_bytes(raw)
        proc = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel", "error",
                "-i", str(source),
                "-map_metadata", "-1",
                "-vn",
                "-ac", str(channels),
                "-ar", str(sample_rate),
                "-codec:a", "libmp3lame",
                "-b:a", f"{bitrate}k",
                str(target),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=90,
        )
        if proc.returncode or not target.exists() or not target.stat().st_size:
            raise ValidationError("Audio optimization failed.")
        content = target.read_bytes()

    metadata = probe_audio_bytes(content, suffix=".mp3")
    metadata["bitrate_kbps"] = bitrate
    return content, metadata
