"""Config API Router — Load and save application configuration"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from core.config import ConfigManager, LLM_PROVIDERS, VAD_PRESETS
from core.models import ContentType
from database.connection import get_db_connection

router = APIRouter()


def _get_config_manager():
    return ConfigManager(get_db_connection)


@router.get("")
def get_config():
    """Load full application config"""
    cm = _get_config_manager()
    config = cm.load()
    return config.to_dict()


class ConfigUpdate(BaseModel):
    config: Dict[str, Any]


@router.put("")
def update_config(body: ConfigUpdate):
    """Save full application config"""
    from core.config import AppConfig
    cm = _get_config_manager()
    try:
        new_config = AppConfig.from_dict(body.config)
        saved = cm.save(new_config)
        return {"saved": saved, "config": new_config.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/providers")
def get_providers():
    """Get available LLM providers"""
    return LLM_PROVIDERS


@router.get("/content-types")
def get_content_types():
    """Get content type options with descriptions"""
    from core.config import get_content_type_display_name, get_content_type_description
    return [
        {
            "value": ct.value,
            "label": get_content_type_display_name(ct),
            "description": get_content_type_description(ct)
        }
        for ct in ContentType
    ]


@router.get("/vad-presets")
def get_vad_presets():
    """Get VAD parameter presets for each content type"""
    return {
        ct.value: params.to_dict()
        for ct, params in VAD_PRESETS.items()
    }
