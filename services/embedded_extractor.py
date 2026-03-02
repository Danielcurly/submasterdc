import subprocess
import json
import shutil
from pathlib import Path
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

def get_video_duration(file_path: str) -> float:
    """Uses ffprobe to get video duration in seconds"""
    cmd = [
        FFPROBE_PATH,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def get_audio_language_info(file_path: str) -> str:
    """Uses ffprobe to return the language tag of the first audio stream"""
    cmd = [
        FFPROBE_PATH,
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=index:stream_tags=language",
        "-of", "json",
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)
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
        "-show_entries", "stream=index,codec_name:stream_tags=language",
        "-of", "json",
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)
        data = json.loads(result.stdout)
        return data.get("streams", [])
    except Exception as e:
        app_logger.error(f"[EmbeddedExtractor] Failed to get embedded subtitles: {e}")
        return []

def extract_embedded_subtitle(file_path: str, target_lang: str, output_path: str) -> bool:
    """Extracts a subtitle track matching the target_lang to output_path"""
    streams = get_embedded_subtitles_info(file_path)
    if not streams:
        return False
        
    target_stream_index = None
    allowed_lang_codes = LANGUAGE_MAP.get(target_lang.lower(), [target_lang.lower()])
    
    # Text-based subtitle codecs that we can extract directly to SRT
    TEXT_CODECS = ['subrip', 'ass', 'mov_text', 'webvtt', 'text']
    
    for stream in streams:
        tags = stream.get("tags", {})
        language = tags.get("language", "").lower()
        codec = stream.get("codec_name", "").lower()
        
        if language in allowed_lang_codes:
            if codec not in TEXT_CODECS:
                app_logger.info(f"[EmbeddedExtractor] Skipping track {stream.get('index')} (codec: {codec}) as it is not text-based.")
                continue
            target_stream_index = stream.get("index")
            break
            
    if target_stream_index is None:
        return False
        
    sub_index = 0
    for stream in streams:
        if stream.get("index") == target_stream_index:
            break
        sub_index += 1
        
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", file_path,
        "-map", f"0:s:{sub_index}",
        "-f", "srt",
        output_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)
        return Path(output_path).exists()
    except subprocess.CalledProcessError as e:
        app_logger.error(f"[EmbeddedExtractor] FFmpeg failed. Command: {' '.join(cmd)}\nStderr: {e.stderr}")
        return False
    except Exception as e:
        app_logger.error(f"[EmbeddedExtractor] Failed to extract subtitle track {target_stream_index}: {e}")
        return False


def get_video_fps(file_path: str) -> float:
    """Uses ffprobe to get video FPS"""
    cmd = [
        FFPROBE_PATH,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
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
