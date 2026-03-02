#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Management Module
Handles application configuration loading, saving, and validation
"""

import json
import copy  # Support deep copy for config caching
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

from core.models import (
    ContentType,
    ProviderConfig,
    WhisperConfig,
    TranslationTask,
    TranslationConfig,
    ExportConfig,
    VADParameters,
    LibraryFolder
)


# ============================================================================
# VAD Parameter Presets
# ============================================================================

VAD_PRESETS = {
    ContentType.MOVIE: VADParameters(
        threshold=0.5,
        min_speech_duration_ms=250,
        min_silence_duration_ms=2000,
        speech_pad_ms=400
    ),
    ContentType.DOCUMENTARY: VADParameters(
        threshold=0.45,
        min_speech_duration_ms=300,
        min_silence_duration_ms=1800,
        speech_pad_ms=500
    ),
    ContentType.VARIETY: VADParameters(
        threshold=0.6,
        min_speech_duration_ms=200,
        min_silence_duration_ms=2500,
        speech_pad_ms=300
    ),
    ContentType.ANIMATION: VADParameters(
        threshold=0.4,
        min_speech_duration_ms=150,
        min_silence_duration_ms=1500,
        speech_pad_ms=350
    ),
    ContentType.LECTURE: VADParameters(
        threshold=0.5,
        min_speech_duration_ms=400,
        min_silence_duration_ms=2500,
        speech_pad_ms=600
    ),
    ContentType.MUSIC: VADParameters(
        threshold=0.7,
        min_speech_duration_ms=500,
        min_silence_duration_ms=3000,
        speech_pad_ms=200
    ),
    ContentType.CUSTOM: VADParameters(
        threshold=0.5,
        min_speech_duration_ms=250,
        min_silence_duration_ms=2000,
        speech_pad_ms=400
    )
}

# Content type descriptions
CONTENT_TYPE_DESCRIPTIONS = {
    ContentType.MOVIE: 'Standard configuration for movies and TV series with clear dialogue. High timeline accuracy.',
    ContentType.DOCUMENTARY: 'Optimized for voiceover recognition, reducing background music interference. Suitable for documentaries, news, and interviews.',
    ContentType.VARIETY: 'High threshold to filter laughter, applause, and background noise. Suitable for variety shows, talk shows, and group interviews.',
    ContentType.ANIMATION: 'Adapted for fast speech delivery, reducing stuttering. Suitable for anime and cartoons.',
    ContentType.LECTURE: 'Focuses on complete sentence recognition, adding pause buffering. Suitable for educational videos, speeches, and training courses.',
    ContentType.MUSIC: 'Extremely high threshold to extract only vocals, ignoring background music. Suitable for MVs, concerts, and singing shows.',
    ContentType.CUSTOM: 'Default configuration, VAD parameters can be manually adjusted for special needs.'
}


# ============================================================================
# LLM Provider Configuration
# ============================================================================

LLM_PROVIDERS = {
    "Ollama (Local)": {
        "base_url": "http://ollama:11434/v1",
        "model": "qwen2.5:7b",
        "help": "No internet required, use local compute"
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "help": "High performance"
    },
    "Google Gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash, gemini-3-flash-preview, gemini-2.5-flash-lite, gemini-3-pro-preview",
        "help": "Modern Google models (v2.5, v3) with automatic rotation"
    },
    "Moonshot (Kimi)": {
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "help": "Optimized for long text"
    },
    "Aliyun (Qwen)": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-turbo",
        "help": "Aliyun Official"
    },
    "ZhipuAI (GLM)": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "help": "Zhipu Official"
    },
    "OpenAI (Official)": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "help": "Stable and powerful"
    },
    "Custom": {
        "base_url": "",
        "model": "",
        "help": "Manual input"
    }
}


# ============================================================================
# App Configuration Class
# ============================================================================

@dataclass
class AppConfig:
    """Application Configuration (Main Class)"""
    
    # Whisper configuration
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    
    # Translation configuration
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    
    # Export configuration
    export: ExportConfig = field(default_factory=ExportConfig)
    
    # Content type
    content_type: ContentType = ContentType.MOVIE
    
    # Current LLM provider
    current_provider: str = 'Ollama (Local)'
    
    # Library folders
    libraries: List[LibraryFolder] = field(default_factory=list)
    
    # Provider configs
    provider_configs: Dict[str, ProviderConfig] = field(default_factory=dict)
    
    def get_vad_parameters(self) -> VADParameters:
        """Get VAD parameters for current content type"""
        return VAD_PRESETS.get(self.content_type, VAD_PRESETS[ContentType.MOVIE])
    
    def get_current_provider_config(self) -> ProviderConfig:
        """Get current provider configuration"""
        if self.current_provider not in self.provider_configs:
            default = LLM_PROVIDERS.get(self.current_provider, {})
            return ProviderConfig(
                api_key='',
                base_url=default.get('base_url', ''),
                model_name=default.get('model', '')
            )
        return self.provider_configs[self.current_provider]
    
    def update_provider_config(
        self, 
        provider: str, 
        api_key: str, 
        base_url: str, 
        model_name: str
    ):
        """Update specified provider configuration"""
        self.provider_configs[provider] = ProviderConfig(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name
        )
        self.current_provider = provider
    
    def to_dict(self) -> Dict:
        """Convert to dictionary (for serialization)"""
        return {
            'whisper': self.whisper.to_dict(),
            'translation': self.translation.to_dict(),
            'export': self.export.to_dict(),
            'content_type': self.content_type.value if isinstance(self.content_type, ContentType) else self.content_type,
            'current_provider': self.current_provider,
            'libraries': [l.to_dict() for l in self.libraries],
            'provider_configs': {
                k: v.to_dict() for k, v in self.provider_configs.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AppConfig':
        """Create config object from dictionary"""
        # Parse Whisper config
        whisper_data = data.get('whisper', {})
        
        # Extract content_type if it was bundled inside whisper
        content_type_str = data.get('content_type', 'movie')
        if 'content_type' in whisper_data:
            content_type_str = whisper_data.pop('content_type')
            
        whisper = WhisperConfig(**whisper_data)
        
        # Parse translation config
        translation_data = data.get('translation', {})
        
        # Extract provider and providers_config if they were bundled inside translation
        if 'provider' in translation_data:
            data['current_provider'] = translation_data.pop('provider')
        if 'providers_config' in translation_data:
            data['provider_configs'] = translation_data.pop('providers_config')
            
        if 'tasks' in translation_data:
            translation_data['tasks'] = [TranslationTask.from_dict(t) for t in translation_data['tasks']]
        translation = TranslationConfig(**translation_data)
        
        # Parse export config
        export_data = data.get('export', {'formats': ['srt']})
        export = ExportConfig.from_dict(export_data)
        
        # Parse content type
        try:
            content_type = ContentType(content_type_str)
        except ValueError:
            content_type = ContentType.MOVIE
        
        # Parse provider configs
        provider_configs_data = data.get('provider_configs', {})
        provider_configs = {
            k: ProviderConfig.from_dict(v) 
            for k, v in provider_configs_data.items()
        }
        
        # Parse libraries
        libraries_data = data.get('libraries', [])
        libraries = [LibraryFolder.from_dict(l) for l in libraries_data]
        
        return cls(
            whisper=whisper,
            translation=translation,
            export=export,
            content_type=content_type,
            current_provider=data.get('current_provider', 'Ollama (Local)'),
            libraries=libraries,
            provider_configs=provider_configs
        )


# ============================================================================
# Configuration Persistence (Database Interaction)
# ============================================================================

class ConfigManager:
    """Config Manager (Handles loading and saving)"""
    
    def __init__(self, db_connection):
        """
        Initialize config manager
        
        Args:
            db_connection: Database connection factory function
        """
        self.get_db = db_connection
        self._last_saved_config_dict = {}  # Cache for last saved/loaded config to avoid redundant DB writes
    
    def load(self) -> AppConfig:
        """Load configuration from database"""
        conn = self.get_db()
        try:
            cursor = conn.execute("SELECT key, value FROM config")
            config_dict = {row[0]: row[1] for row in cursor.fetchall()}
            
            if not config_dict:
                # Initialize default config and cache it
                default_config = AppConfig()
                self._last_saved_config_dict = default_config.to_dict()
                return default_config
            
            # Handle migrations for translation tasks
            raw_tasks = config_dict.get('translation_tasks')
            if raw_tasks:
                tasks = json.loads(raw_tasks)
            else:
                old_langs = json.loads(config_dict.get('target_languages', '["en"]'))
                bilingual = config_dict.get('bilingual_subtitles', 'false') == 'true'
                sec_lang = config_dict.get('secondary_language', 'en')
                file_code = config_dict.get('bilingual_filename_code', 'primary')
                tasks = [
                    {
                        'target_language': lang,
                        'bilingual_subtitles': bilingual,
                        'secondary_language': sec_lang,
                        'bilingual_filename_code': file_code
                    } for lang in old_langs
                ]
            
            # Migrate old library_paths to libraries if needed
            if 'libraries' in config_dict:
                libraries = json.loads(config_dict['libraries'])
            else:
                old_paths = json.loads(config_dict.get('library_paths', '["/media"]'))
                import uuid
                libraries = [
                    {'id': str(uuid.uuid4())[:8], 'name': p.split('/')[-1] if '/' in p else (p.split('\\')[-1] if '\\' in p else p), 'path': p, 'scan_mode': 'manual', 'scan_interval_hours': 24}
                    for p in old_paths
                ]
            
            # Construct nested configuration dictionary
            data = {
                'whisper': {
                    'model_size': config_dict.get('whisper_model', 'base'),
                    'compute_type': config_dict.get('compute_type', 'int8'),
                    'device': config_dict.get('device', 'cpu'),
                    'source_language': config_dict.get('source_language', 'auto'),
                    'cpu_threads': int(config_dict.get('cpu_threads', 4))
                },
                'translation': {
                    'enabled': config_dict.get('enable_translation', 'false') == 'true',
                    'tasks': tasks,
                    'max_lines_per_batch': int(config_dict.get('max_lines_per_batch', 500)),
                    'max_daily_calls': int(config_dict.get('max_daily_calls', 0))
                },
                'export': json.loads(config_dict.get('export_formats', '{"formats": ["ass"]}')),
                'content_type': config_dict.get('content_type', 'movie'),
                'current_provider': config_dict.get('current_provider', 'Ollama (Local)'),
                'libraries': libraries,
                'provider_configs': json.loads(config_dict.get('provider_configs', '{}'))
            }
            
            # Update cache after loading
            loaded_config = AppConfig.from_dict(data)
            self._last_saved_config_dict = loaded_config.to_dict()
            return loaded_config
            
        finally:
            conn.close()
    
    def save(self, config: AppConfig) -> bool:
        """
        Save configuration to database
        
        Returns:
            bool: True if execution occurred, False if no changes
        """
        # Compare with last saved config to avoid redundant operations
        new_config_dict = config.to_dict()
        
        if new_config_dict == self._last_saved_config_dict:
            return False

        conn = self.get_db()
        try:
            # Flatten configuration
            flat_config = {
                'whisper_model': config.whisper.model_size,
                'compute_type': config.whisper.compute_type,
                'device': config.whisper.device,
                'source_language': config.whisper.source_language,
                'cpu_threads': str(config.whisper.cpu_threads),
                'enable_translation': 'true' if config.translation.enabled else 'false',
                'translation_tasks': json.dumps([t.to_dict() for t in config.translation.tasks]),
                'max_lines_per_batch': str(config.translation.max_lines_per_batch),
                'max_daily_calls': str(config.translation.max_daily_calls),
                'export_formats': json.dumps(config.export.to_dict(), ensure_ascii=False),
                'content_type': config.content_type.value if isinstance(config.content_type, ContentType) else config.content_type,
                'current_provider': config.current_provider,
                'libraries': json.dumps([l.to_dict() for l in config.libraries]),
                'provider_configs': json.dumps(
                    {k: v.to_dict() for k, v in config.provider_configs.items()},
                    ensure_ascii=False
                )
            }
            
            for key, value in flat_config.items():
                conn.execute(
                    "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                    (key, str(value))
                )
            
            conn.commit()
            
            # Update cache after successful save
            self._last_saved_config_dict = copy.deepcopy(new_config_dict)
            return True
            
        except Exception as e:
            print(f"Failed to save config: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()


# ============================================================================
# Helper Functions
# ============================================================================

def get_content_type_display_name(content_type: ContentType) -> str:
    """Get display name for content type"""
    display_names = {
        ContentType.MOVIE: '🎬 Movies/TV (Standard)',
        ContentType.DOCUMENTARY: '📺 Documentaries/News',
        ContentType.VARIETY: '🎤 Variety/Talk Shows',
        ContentType.ANIMATION: '🎨 Animation/Anime',
        ContentType.LECTURE: '🎓 Lectures/Courses',
        ContentType.MUSIC: '🎵 Music Videos/MVs',
        ContentType.CUSTOM: '⚙️ Custom'
    }
    return display_names.get(content_type, content_type.value)


def get_content_type_description(content_type: ContentType) -> str:
    """Get detailed description for content type"""
    return CONTENT_TYPE_DESCRIPTIONS.get(
        content_type, 
        'Default Configuration'
    )