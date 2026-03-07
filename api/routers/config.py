"""Config API Router — Load and save application configuration"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

from core.config import ConfigManager, LLM_PROVIDERS, VAD_PRESETS
from core.models import ContentType, StandardResponse
from database.connection import get_db_connection
from api.deps import get_config_manager

router = APIRouter()


@router.get("", response_model=StandardResponse)
def get_config():
    """Load full application config"""
    cm = get_config_manager()
    config = cm.load()
    return StandardResponse(success=True, message="Config loaded", data=config.to_dict())


class ConfigUpdate(BaseModel):
    config: Dict[str, Any]


@router.put("", response_model=StandardResponse)
def update_config(body: ConfigUpdate):
    """Save full application config"""
    from core.config import AppConfig
    cm = get_config_manager()
    try:
        from core.logger import app_logger
        new_config = AppConfig.from_dict(body.config)
        saved = cm.save(new_config)
        app_logger.info(f"[ConfigAPI] Configuration saved and applied. Log level: {new_config.log_level}")
        return StandardResponse(success=True, message="Config saved", data={"saved": saved, "config": new_config.to_dict()})
    except Exception as e:
        return StandardResponse(success=False, message=str(e))


@router.get("/subtitles", response_model=StandardResponse)
def get_subtitle_style():
    """Get current subtitle style configuration"""
    cm = get_config_manager()
    config = cm.load()
    return StandardResponse(success=True, message="Style loaded", data=config.subtitle_style.to_dict())


@router.put("/subtitles", response_model=StandardResponse)
def update_subtitle_style(style_dict: Dict[str, Any]):
    """Update subtitle style configuration"""
    from core.models import SubtitleStyleConfig
    cm = get_config_manager()
    try:
        config = cm.load()
        config.subtitle_style = SubtitleStyleConfig.from_dict(style_dict)
        saved = cm.save(config)
        return StandardResponse(success=True, message="Style updated", data={"saved": saved, "style": config.subtitle_style.to_dict()})
    except Exception as e:
        return StandardResponse(success=False, message=str(e))


@router.get("/vad-presets", response_model=StandardResponse)
def get_vad_presets():
    """Get VAD parameter presets for each content type"""
    data = {
        ct.value: params.to_dict()
        for ct, params in VAD_PRESETS.items()
    }
    return StandardResponse(success=True, message="VAD presets loaded", data=data)
