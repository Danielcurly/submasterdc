#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Model Definitions
Central management for all data structures
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# ============================================================================
# Enums
# ============================================================================

class TaskStatus(Enum):
    """Task Status"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    SKIPPED = 'skipped'


class ScanMode(Enum):
    """Library folder scan modes"""
    MANUAL = 'manual'
    PERIODIC = 'periodic'
    AUTOMATIC = 'automatic'


class ContentType(Enum):
    """Video Content Type (affects VAD parameters)"""
    MOVIE = 'movie'              # Movies/TV Series
    DOCUMENTARY = 'documentary'  # Documentaries/News
    VARIETY = 'variety'          # Variety/Talk Shows
    ANIMATION = 'animation'      # Animation/Anime
    LECTURE = 'lecture'          # Lectures/Courses
    MUSIC = 'music'              # Music Videos/MVs
    CUSTOM = 'custom'            # Custom


# ============================================================================
# Subtitle Related Models
# ============================================================================

@dataclass
class SubtitleInfo:
    """Subtitle file info"""
    path: str
    lang: str
    tag: str
    is_app_generated: bool = False
    is_bilingual: bool = False
    primary_lang: Optional[str] = None
    secondary_lang: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'path': self.path,
            'lang': self.lang,
            'tag': self.tag,
            'is_app_generated': self.is_app_generated,
            'is_bilingual': self.is_bilingual,
            'primary_lang': self.primary_lang,
            'secondary_lang': self.secondary_lang
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SubtitleInfo':
        return cls(
            path=data['path'],
            lang=data['lang'],
            tag=data['tag'],
            is_app_generated=data.get('is_app_generated', False),
            is_bilingual=data.get('is_bilingual', False),
            primary_lang=data.get('primary_lang'),
            secondary_lang=data.get('secondary_lang')
        )


@dataclass
class SubtitleEntry:
    """General subtitle entry"""
    index: str
    timecode: str
    text: str
    
    def to_dict(self) -> Dict:
        return {
            'index': self.index,
            'timecode': self.timecode,
            'text': self.text
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SubtitleEntry':
        return cls(
            index=str(data.get('index', '1')),
            timecode=str(data.get('timecode', '00:00:00,000 --> 00:00:01,000')),
            text=str(data.get('text', ''))
        )


# ============================================================================
# Library Models
# ============================================================================

@dataclass
class LibraryFolder:
    """Library folder configuration"""
    id: str
    name: str
    path: str
    scan_mode: ScanMode = ScanMode.MANUAL
    scan_interval_hours: float = 24.0
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'path': self.path,
            'scan_mode': self.scan_mode.value if isinstance(self.scan_mode, ScanMode) else self.scan_mode,
            'scan_interval_hours': self.scan_interval_hours
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'LibraryFolder':
        scan_mode_val = data.get('scan_mode', 'manual')
        scan_mode = ScanMode(scan_mode_val) if isinstance(scan_mode_val, str) else scan_mode_val
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            path=data.get('path', ''),
            scan_mode=scan_mode,
            scan_interval_hours=float(data.get('scan_interval_hours', 24))
        )


# ============================================================================
# Configuration Models
# ============================================================================

@dataclass
class VADParameters:
    """VAD (Voice Activity Detection) Parameters"""
    threshold: float
    min_speech_duration_ms: int
    min_silence_duration_ms: int
    speech_pad_ms: int
    
    def to_dict(self) -> Dict:
        return {
            'threshold': self.threshold,
            'min_speech_duration_ms': self.min_speech_duration_ms,
            'min_silence_duration_ms': self.min_silence_duration_ms,
            'speech_pad_ms': self.speech_pad_ms
        }


@dataclass
class ProviderConfig:
    """LLM Provider Config"""
    api_key: str = ''
    base_url: str = ''
    model_name: str = ''
    
    def to_dict(self) -> Dict:
        return {
            'api_key': self.api_key,
            'base_url': self.base_url,
            'model_name': self.model_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProviderConfig':
        return cls(
            api_key=data.get('api_key', ''),
            base_url=data.get('base_url', ''),
            model_name=data.get('model_name', '')
        )


@dataclass
class WhisperConfig:
    """Whisper Model Config"""
    model_size: str = 'base'
    compute_type: str = 'int8'
    device: str = 'cpu'
    source_language: str = 'auto'
    cpu_threads: int = 4
    
    def to_dict(self) -> Dict:
        return {
            'model_size': self.model_size,
            'compute_type': self.compute_type,
            'device': self.device,
            'source_language': self.source_language,
            'cpu_threads': self.cpu_threads
        }


@dataclass
class TranslationTask:
    """Individual Translation Task Rules"""
    target_language: str
    bilingual_subtitles: bool = False
    secondary_language: str = 'en'
    bilingual_filename_code: str = 'primary'
    
    def to_dict(self) -> Dict:
        return {
            'target_language': self.target_language,
            'bilingual_subtitles': self.bilingual_subtitles,
            'secondary_language': self.secondary_language,
            'bilingual_filename_code': self.bilingual_filename_code
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TranslationTask':
        bi_sub = data.get('bilingual_subtitles', False)
        if isinstance(bi_sub, str):
            bi_sub = bi_sub.lower() == 'true'
            
        return cls(
            target_language=data.get('target_language', 'en'),
            bilingual_subtitles=bi_sub,
            secondary_language=data.get('secondary_language', 'en'),
            bilingual_filename_code=data.get('bilingual_filename_code', 'primary')
        )


@dataclass
class TranslationConfig:
    """Translation Config"""
    enabled: bool = False
    tasks: List[TranslationTask] = field(default_factory=list)
    max_lines_per_batch: int = 500
    max_retries: int = 3
    timeout: int = 180
    
    def to_dict(self) -> Dict:
        return {
            'enabled': self.enabled,
            'tasks': [t.to_dict() for t in self.tasks],
            'max_lines_per_batch': self.max_lines_per_batch,
            'max_retries': self.max_retries,
            'timeout': self.timeout
        }


@dataclass
class ExportConfig:
    """Export Config"""
    formats: List[str] = field(default_factory=lambda: ['ass'])
    
    def to_dict(self) -> Dict:
        return {'formats': self.formats}
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ExportConfig':
        # Ensure only supported formats are loaded
        formats_data = data.get('formats', ['srt', 'ass'])
        if not isinstance(formats_data, list):
            formats_data = ['srt', 'ass']
        formats: List[str] = [str(f) for f in formats_data if str(f) in ['srt', 'ass']]
        if not formats:
            formats = ['ass']
        return cls(formats=formats)


# ============================================================================
# Task Model
# ============================================================================

@dataclass
class Task:
    """Task Entity"""
    id: int
    file_path: str
    status: TaskStatus
    progress: int = 0
    log: str = ''
    params: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'file_path': self.file_path,
            'status': self.status.value if isinstance(self.status, TaskStatus) else self.status,
            'progress': self.progress,
            'log': self.log,
            'params': self.params,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        status = data['status']
        if isinstance(status, str):
            status = TaskStatus(status)
        
        return cls(
            id=data['id'],
            file_path=data['file_path'],
            status=status,
            progress=data.get('progress', 0),
            log=data.get('log', ''),
            params=data.get('params'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )


# ============================================================================
# Media File Model
# ============================================================================

@dataclass
class MediaFile:
    """Media File Entity"""
    id: int
    file_path: str
    file_name: str
    file_size: int
    subtitles: List[SubtitleInfo] = field(default_factory=list)
    has_translated: bool = False
    updated_at: Optional[str] = None
    
    @property
    def has_subtitle(self) -> bool:
        """Whether it has subtitles"""
        return len(self.subtitles) > 0
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'subtitles': [s.to_dict() for s in self.subtitles],
            'has_subtitle': self.has_subtitle,
            'has_translated': self.has_translated,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MediaFile':
        subtitles_data = data.get('subtitles', [])
        if isinstance(subtitles_data, str):
            import json
            subtitles_data = json.loads(subtitles_data)
        
        subtitles = [SubtitleInfo.from_dict(s) for s in subtitles_data]
        
        return cls(
            id=data['id'],
            file_path=data['file_path'],
            file_name=data['file_name'],
            file_size=data['file_size'],
            subtitles=subtitles,
            has_translated=data.get('has_translated', False),
            updated_at=data.get('updated_at')
        )


# ============================================================================
# Constants
# ============================================================================

# Supported video formats
SUPPORTED_VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.mov', '.avi', 
    '.flv', '.wmv', '.m4v', '.webm', '.ts'
}

# Supported subtitle formats
SUPPORTED_SUBTITLE_FORMATS = {
    'srt', 'vtt', 'ass', 'ssa', 'sub'
}

# Language code mapping
ISO_LANG_MAP = {
    'auto': 'Auto Detect',
    'en': 'English', 'zh': 'Chinese', 'de': 'German', 'es': 'Spanish', 'ru': 'Russian',
    'ko': 'Korean', 'fr': 'French', 'ja': 'Japanese', 'pt': 'Portuguese', 'tr': 'Turkish',
    'pl': 'Polish', 'ca': 'Catalan', 'nl': 'Dutch', 'ar': 'Arabic', 'sv': 'Swedish',
    'it': 'Italian', 'id': 'Indonesian', 'hi': 'Hindi', 'fi': 'Finnish', 'vi': 'Vietnamese',
    'he': 'Hebrew', 'uk': 'Ukrainian', 'el': 'Greek', 'ms': 'Malay', 'cs': 'Czech',
    'ro': 'Romanian', 'da': 'Danish', 'hu': 'Hungarian', 'ta': 'Tamil', 'no': 'Norwegian',
    'th': 'Thai', 'ur': 'Urdu', 'hr': 'Croatian', 'bg': 'Bulgarian', 'lt': 'Lithuanian',
    'la': 'Latin', 'mi': 'Maori', 'ml': 'Malayalam', 'cy': 'Welsh', 'sk': 'Slovak',
    'te': 'Telugu', 'fa': 'Persian', 'lv': 'Latvian', 'bn': 'Bengali', 'sr': 'Serbian',
    'az': 'Azerbaijani', 'sl': 'Slovenian', 'kn': 'Kannada', 'et': 'Estonian', 'mk': 'Macedonian',
    'br': 'Breton', 'eu': 'Basque', 'is': 'Icelandic', 'hy': 'Armenian', 'ne': 'Nepali',
    'mn': 'Mongolian', 'bs': 'Bosnian', 'kk': 'Kazakh', 'sq': 'Albanian', 'sw': 'Swahili',
    'gl': 'Galician', 'mr': 'Marathi', 'pa': 'Punjabi', 'si': 'Sinhala', 'km': 'Khmer',
    'sn': 'Shona', 'yo': 'Yoruba', 'so': 'Somali', 'af': 'Afrikaans', 'oc': 'Occitan',
    'ka': 'Georgian', 'be': 'Belarusian', 'tg': 'Tajik', 'sd': 'Sindhi', 'gu': 'Gujarati',
    'am': 'Amharic', 'yi': 'Yiddish', 'lo': 'Lao', 'uz': 'Uzbek', 'fo': 'Faroese',
    'ht': 'Haitian Creole', 'ps': 'Pashto', 'tk': 'Turkmen', 'nn': 'Nynorsk', 'mt': 'Maltese',
    'sa': 'Sanskrit', 'lb': 'Luxembourgish', 'my': 'Myanmar', 'bo': 'Tibetan', 'tl': 'Tagalog',
    'mg': 'Malagasy', 'as': 'Assamese', 'tt': 'Tatar', 'haw': 'Hawaiian', 'ln': 'Lingala',
    'ha': 'Hausa', 'ba': 'Bashkir', 'jw': 'Javanese', 'su': 'Sundanese',
    'chs': 'Simplified Chinese', 'cht': 'Traditional Chinese', 'eng': 'English', 
    'jpn': 'Japanese', 'kor': 'Korean', 'unknown': 'Unknown'
}

# Target language options (Sorted by English name)
TARGET_LANG_OPTIONS = sorted([
    'en', 'zh', 'de', 'es', 'ru', 'ko', 'fr', 'ja', 'pt', 'tr', 'pl', 'ca', 'nl', 'ar', 'sv', 'it', 'id', 'hi', 'fi', 'vi', 
    'he', 'uk', 'el', 'ms', 'cs', 'ro', 'da', 'hu', 'ta', 'no', 'th', 'ur', 'hr', 'bg', 'lt', 'la', 'mi', 'ml', 'cy', 'sk', 
    'te', 'fa', 'lv', 'bn', 'sr', 'az', 'sl', 'kn', 'et', 'mk', 'br', 'eu', 'is', 'hy', 'ne', 'mn', 'bs', 'kk', 'sq', 'sw', 
    'gl', 'mr', 'pa', 'si', 'km', 'sn', 'yo', 'so', 'af', 'oc', 'ka', 'be', 'tg', 'sd', 'gu', 'am', 'yi', 'lo', 'uz', 'fo', 
    'ht', 'ps', 'tk', 'nn', 'mt', 'sa', 'lb', 'my', 'bo', 'tl', 'mg', 'as', 'tt', 'haw', 'ln', 'ha', 'ba', 'jw', 'su'
], key=lambda x: ISO_LANG_MAP.get(x, x))