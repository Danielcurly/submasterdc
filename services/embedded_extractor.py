import subprocess
import json
import shutil
from pathlib import Path
import shlex
from core.logger import app_logger

# Resolve ffmpeg/ffprobe: prefer system PATH, fallback to known locations
def _find_exe(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    # Generic fallbacks if not in PATH (environment specific ones removed for portability)
    fallbacks = [] 
    for fb in fallbacks:
        if Path(fb).exists():
            return fb
    return name  # Last resort: hope shell finds it

FFPROBE_PATH = _find_exe("ffprobe")
FFMPEG_PATH = _find_exe("ffmpeg")
app_logger.info(f"[EmbeddedExtractor] Using ffprobe: {FFPROBE_PATH}")
app_logger.info(f"[EmbeddedExtractor] Using ffmpeg: {FFMPEG_PATH}")

LANGUAGE_MAP = {
    'en': ['en', 'eng', 'english'],
    'zh': ['zh', 'chi', 'zho', 'chinese'],
    'chs': ['zh', 'chi', 'zho', 'chinese'],
    'cht': ['zh', 'chi', 'zho', 'chinese'],
    'es': ['es', 'spa', 'spanish'],
    'ja': ['ja', 'jpn', 'japanese'],
    'ko': ['ko', 'kor', 'korean'],
    'fr': ['fr', 'fre', 'fra', 'french'],
    'de': ['de', 'ger', 'deu', 'german'],
    'ru': ['ru', 'rus', 'russian'],
}

# Text-based subtitle codecs that ffmpeg can extract to SRT
TEXT_CODECS = ['subrip', 'ass', 'ssa', 'mov_text', 'webvtt', 'text', 'srt']

def get_video_duration(file_path: str) -> float:
    """Uses ffprobe to get video duration in seconds"""
    cmd = [
        FFPROBE_PATH,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(Path(file_path).resolve())
    ]
    try:
        app_logger.debug(f"[EmbeddedExtractor] Running ffprobe: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)
        app_logger.debug(f"[EmbeddedExtractor] ffprobe output: {result.stdout.strip()}")
        return float(result.stdout.strip())
    except Exception as e:
        app_logger.debug(f"[EmbeddedExtractor] ffprobe failed: {e}")
        return 0.0


def get_audio_language_info(file_path: str) -> str:
    """Uses ffprobe to return the language tag of the first audio stream.
    Returns 'und' (undetermined) on failure — callers should treat this as 'auto'."""
    cmd = [
        FFPROBE_PATH,
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=tags",
        "-of", "json",
        str(Path(file_path).resolve())
    ]
    try:
        app_logger.debug(f"[EmbeddedExtractor] Running ffprobe: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)
        app_logger.debug(f"[EmbeddedExtractor] ffprobe result: {result.stdout.strip()}")
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if streams:
             tags = streams[0].get("tags", {})
             lang = tags.get("language", "en").lower()
             return lang
    except Exception as e:
        app_logger.error(f"[EmbeddedExtractor] Failed to get audio language: {e}")
    return "und" # Fallback to und


def get_embedded_subtitles_info(file_path: str) -> list:
    """Uses ffprobe to list subtitle streams in a video"""
    cmd = [
        FFPROBE_PATH,
        "-v", "error",
        "-select_streams", "s",
        "-show_entries", "stream=index,codec_name,tags",
        "-of", "json",
        str(Path(file_path).resolve())
    ]
    try:
        app_logger.debug(f"[EmbeddedExtractor] Running ffprobe: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)
        app_logger.debug(f"[EmbeddedExtractor] ffprobe result: {result.stdout.strip()}")
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        app_logger.info(f"[EmbeddedExtractor] Found {len(streams)} subtitle streams in file.")
        return streams
    except Exception as e:
        app_logger.error(f"[EmbeddedExtractor] Failed to get embedded subtitles: {e}")
        return []

def detect_embedded_languages(file_path: str, temp_dir: str) -> dict[str, int]:
    """
    Quickly detects languages of all embedded text subtitle tracks.
    Returns a dict mapping language code to the FIRST stream index found for that language.
    
    Performance Optimization: Instead of extracting full tracks, it extracts 
    a 2-minute snippet from the middle of the video for each track.
    """
    streams = get_embedded_subtitles_info(file_path)
    if not streams:
        return {}

    duration = get_video_duration(file_path)
    # Start 2 minutes of probe from the middle, or from start if short
    seek_time = max(0.0, (float(duration) / 2.0) - 60.0)
    
    import os
    from utils.lang_detection import detect_language_from_subtitle

    detected_map = {}
    
    for stream in streams:
        idx = stream.get("index")
        codec = stream.get("codec_name", "").lower()
        
        if codec not in TEXT_CODECS:
            app_logger.info(f"[EmbeddedExtractor] Skipping track {idx} (codec '{codec}' is not text-based)")
            continue
            
        snippet_path = os.path.join(temp_dir, f"snippet_{idx}.srt")
        
        # Extract 600s snippet from middle
        app_logger.info(f"[EmbeddedExtractor] Probing text track {idx} ({codec}) from t={seek_time:.1f}s")
        if _run_ffmpeg_extract(file_path, idx, streams, snippet_path, ss=seek_time, t=600):
            if os.path.exists(snippet_path) and os.path.getsize(snippet_path) > 10:
                detected = detect_language_from_subtitle(snippet_path)
                
                from utils.lang_utils import normalize_language_code
                norm = normalize_language_code(detected)
                
                app_logger.info(f"[EmbeddedExtractor] Track {idx} snippet ({codec}) detected as: {norm}")
                
                # Keep the first track found for each language
                if norm not in detected_map:
                    detected_map[norm] = idx
            else:
                app_logger.warning(f"[EmbeddedExtractor] Track {idx} snippet was empty or too small.")
            
            # Clean up snippet immediately
            try:
                if os.path.exists(snippet_path):
                    os.remove(snippet_path)
            except Exception as e:
                app_logger.warning(f"[EmbeddedExtractor] Could not delete temporary snippet {snippet_path}: {e}")
        else:
            app_logger.error(f"[EmbeddedExtractor] Failed to extract snippet for track {idx}")
                
    return detected_map

def extract_single_subtitle(file_path: str, stream_index: int, output_path: str) -> bool:
    """Performs a full extraction of a specific embedded subtitle track."""
    streams = get_embedded_subtitles_info(file_path)
    return _run_ffmpeg_extract(file_path, stream_index, streams, output_path)

# Legacy support for main worker loop if not yet updated
def extract_all_text_subtitles(file_path: str, output_dir: str, selective_indices: list[int] = None) -> dict[str, list[str]]:
    """Legacy wrapper. Now performs full extraction of specified indices (or all)."""
    streams = get_embedded_subtitles_info(file_path)
    if not streams: return {}
    
    import os
    from utils.lang_detection import detect_language_from_subtitle
    
    res = {}
    for s in streams:
        idx = s.get("index")
        if selective_indices and idx not in selective_indices: continue
        if s.get("codec_name", "").lower() not in TEXT_CODECS: continue
        
        target = os.path.join(output_dir, f"track_{idx}.srt")
        if extract_single_subtitle(file_path, idx, target):
            if os.path.exists(target) and os.path.getsize(target) > 512:
                lang = detect_language_from_subtitle(target)
                from utils.lang_utils import normalize_language_code
                norm = normalize_language_code(lang)
                if norm not in res: res[norm] = []
                res[norm].append(target)
    return res

from typing import Optional

def _run_ffmpeg_extract(file_path: str, stream_index: int, streams: list, output_path: str, ss: Optional[float] = None, t: Optional[float] = None) -> bool:
    """Helper to run ffmpeg extraction for a specific stream index."""
    sub_index = 0
    for stream in streams:
        if stream.get("index") == stream_index:
            break
        sub_index += 1
        
    cmd = [FFMPEG_PATH, "-y"]
    
    # Fast seek if requested
    if ss is not None:
        cmd.extend(["-ss", str(ss)])
        
    cmd.extend(["-i", str(Path(file_path).resolve())])
    
    # Mapping
    cmd.extend(["-map", f"0:s:{sub_index}"])
    
    # Duration limit
    if t is not None:
        cmd.extend(["-t", str(t)])
        
    cmd.extend([
        "-f", "srt",
        str(Path(output_path).resolve())
    ])
    try:
        app_logger.debug(f"[EmbeddedExtractor] Running ffmpeg: {' '.join(cmd)}")
        subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)
        return Path(output_path).exists()
    except Exception as e:
        app_logger.error(f"[EmbeddedExtractor] Failed to extract subtitle track {stream_index}: {e}")
        return False


def get_video_fps(file_path: str) -> float:
    """Uses ffprobe to get video FPS"""
    cmd = [
        FFPROBE_PATH,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(Path(file_path).resolve())
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)
        rate_str = result.stdout.strip()
        if '/' in rate_str:
            num, den = map(int, rate_str.split('/'))
            return num / den if den != 0 else 25.0
        return float(rate_str) if rate_str else 25.0
    except Exception:
        return 25.0
