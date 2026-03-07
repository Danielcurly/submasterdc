"""AI API Router — AI configuration, connection testing, model discovery"""

import concurrent.futures
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from core.config import LLM_PROVIDERS, ConfigManager
from core.models import ISO_LANG_MAP, TARGET_LANG_OPTIONS, ContentType, StandardResponse
from database.connection import get_db_connection
from api.deps import get_config_manager

router = APIRouter()


class TestConnectionRequest(BaseModel):
    api_key: str
    base_url: str
    model: str


@router.post("/test", response_model=StandardResponse)
def test_connection(body: TestConnectionRequest):
    """Test API connection to an LLM provider (10s timeout)"""
    def _do_test():
        try:
            from services.translator import TranslationConfig, SubtitleTranslator, SubtitleEntry
            config = TranslationConfig(
                api_key=body.api_key,
                base_url=body.base_url,
                model_name=body.model,
                target_language='en'
            )
            translator = SubtitleTranslator(config)
            test_entry = SubtitleEntry(index=1, start_ms=0, end_ms=1000, text="Hello")
            translator._translate_batch([test_entry])
            return True, "Connection succeeded"
        except Exception as e:
            return False, str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_do_test)
        try:
            success, message = future.result(timeout=10)
            return StandardResponse(success=success, message=message)
        except concurrent.futures.TimeoutError:
            return StandardResponse(success=False, message="Connection timeout (10s)")


@router.get("/providers", response_model=StandardResponse)
def get_providers():
    """List available LLM providers with their defaults"""
    return StandardResponse(success=True, message="Providers loaded", data=LLM_PROVIDERS)


@router.get("/ollama-models", response_model=StandardResponse)
def get_ollama_models(base_url: str = "http://ollama:11434/v1"):
    """Fetch available Ollama models"""
    try:
        root_url = base_url.replace("/v1", "").rstrip("/")
        resp = requests.get(f"{root_url}/api/tags", timeout=2.0)
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json().get('models', [])]
            return StandardResponse(success=True, message="Ollama models loaded", data=models)
    except Exception as e:
        return StandardResponse(success=False, message=f"Failed to fetch Ollama models: {e}", data=[])
    return StandardResponse(success=True, message="No Ollama models found", data=[])


@router.get("/languages", response_model=StandardResponse)
def get_languages():
    """Get language options for translation configuration"""
    return StandardResponse(success=True, message="Languages loaded", data={
        "iso_map": ISO_LANG_MAP,
        "target_options": TARGET_LANG_OPTIONS
    })


@router.get("/content-types", response_model=StandardResponse)
def get_content_types():
    """Get content type options"""
    from core.config import get_content_type_display_name, get_content_type_description
    types = [
        {
            "value": ct.value,
            "label": get_content_type_display_name(ct),
            "description": get_content_type_description(ct)
        }
        for ct in ContentType
    ]
    return StandardResponse(success=True, message="Content types loaded", data=types)

@router.get("/usage", response_model=StandardResponse)
def get_usage():
    """Get current AI usage info (used / limit)"""
    cm = get_config_manager()
    return StandardResponse(success=True, message="Usage info loaded", data=cm.get_usage_info())
