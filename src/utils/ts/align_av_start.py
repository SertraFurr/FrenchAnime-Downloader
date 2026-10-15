"""Re-align the audio with the picture when a stream starts too early.

Most HLS packagers write the first audio sample at the DTS of the first video
packet, not at its PTS. With B-frames the picture is displayed later than it is
decoded (has_b_frames=2 at 23.976 fps: about 83 ms), so the sound plays that much
before the image it belongs to. The offset is visible in the file itself:

    video  pts 0.184   dts 0.100   <- first displayed frame
    audio  pts 0.101              <- aligned on the video DTS, not on its PTS

align_av_start() detects exactly that layout and delays the audio by the missing
amount (stream copy, nothing is re-encoded). A file whose streams are already
aligned is left untouched.
"""
import json
import os
import subprocess

from src.var import print_status

# What counts as the reorder delay of a video: from one frame at 60 fps to a few frames at 24 fps.
MIN_DELAY = 0.015
MAX_DELAY = 0.350
# The audio start must sit on the video DTS (give or take this much) for the layout to match.
DTS_TOLERANCE = 0.020


def _ffprobe_json(path, *args):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", *args, path],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except ValueError:
        return None


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def measure_av_offset(path):
    """Returns the delay to apply to the audio (seconds), or None if the file is fine / unreadable."""
    streams = _ffprobe_json(path, "-show_entries", "stream=index,codec_type,start_time")
    if not streams:
        return None
    video = next((s for s in streams.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not video or not audio:
        return None
    video_start, audio_start = _float(video.get("start_time")), _float(audio.get("start_time"))
    if video_start is None or audio_start is None:
        return None

    packets = _ffprobe_json(path, "-select_streams", "v:0", "-show_entries", "packet=pts_time,dts_time",
                            "-read_intervals", "%+#8")
    pairs = [(_float(p.get("pts_time")), _float(p.get("dts_time"))) for p in (packets or {}).get("packets", [])]
    pairs = [(p, d) for p, d in pairs if p is not None and d is not None]
    if not pairs:
        return None
    first_dts = min(d for _, d in pairs)
    first_pts = min(p for p, _ in pairs)

    delay = video_start - audio_start
    reorder = first_pts - first_dts
    if not (MIN_DELAY <= delay <= MAX_DELAY and reorder >= MIN_DELAY):
        return None
    if abs(audio_start - first_dts) > DTS_TOLERANCE:
        return None                       # not the DTS-aligned layout: do not guess
    return delay


def align_av_start(path):
    """Delay the audio of `path` (mp4/mkv) in place when it starts ahead of the picture.
    Returns True when the file was rewritten. Never raises: on any doubt the file is kept as is."""
    try:
        if not path or not os.path.exists(path):
            return False
        delay = measure_av_offset(path)
        if delay is None:
            return False

        root, ext = os.path.splitext(path)
        temp = root + ".av_aligned" + ext
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostats",
            "-i", path,
            "-itsoffset", f"{delay:.3f}", "-i", path,
            "-map", "0:v", "-map", "1:a", "-map", "0:s?",
            "-c", "copy",
            temp,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        if result.returncode != 0 or not os.path.exists(temp) or os.path.getsize(temp) < 1024:
            if os.path.exists(temp):
                os.remove(temp)
            return False

        # check the result before replacing anything: the starts must now match
        streams = _ffprobe_json(temp, "-show_entries", "stream=codec_type,start_time") or {}
        starts = {s.get("codec_type"): _float(s.get("start_time")) for s in streams.get("streams", [])}
        v, a = starts.get("video"), starts.get("audio")
        if v is None or a is None or abs(v - a) > 0.010:
            os.remove(temp)
            return False

        os.replace(temp, path)
        print_status(f"Audio was {delay * 1000:.0f} ms ahead of the picture, re-aligned.", "info")
        return True
    except Exception:
        try:
            if 'temp' in locals() and os.path.exists(temp):
                os.remove(temp)
        except Exception:
            pass
        return False
