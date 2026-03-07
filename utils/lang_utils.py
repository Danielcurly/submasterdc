#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Language Utilities
Centralized language code normalization and mapping
"""

# Project standard language codes: zh, en, ja, ko, fr, de, ru, es
LANGUAGE_NORMALIZATION_MAP = {
    # Chinese variants
    'zh': 'zh',
    'chs': 'zh',
    'cht': 'zh',
    'chi': 'zh',
    'zho': 'zh',
    'chinese': 'zh',
    'zh-cn': 'zh',
    'zh-tw': 'zh',
    'zh-hk': 'zh',
    
    # English variants
    'en': 'en',
    'eng': 'en',
    'english': 'en',
    
    # Spanish variants
    'es': 'es',
    'spa': 'es',
    'spanish': 'es',
    
    # Japanese variants
    'ja': 'ja',
    'jpn': 'ja',
    'japanese': 'ja',
    
    # Korean variants
    'ko': 'ko',
    'kor': 'ko',
    'korean': 'ko',
    
    # French variants
    'fr': 'fr',
    'fre': 'fr',
    'fra': 'fr',
    'french': 'fr',
    
    # German variants
    'de': 'de',
    'ger': 'de',
    'deu': 'de',
    'german': 'de',
    
    # Russian variants
    'ru': 'ru',
    'rus': 'ru',
    'russian': 'ru',
}

def normalize_language_code(lang: str) -> str:
    """
    Normalize language code to project standard (e.g., 'chs' -> 'zh', 'eng' -> 'en')
    
    Args:
        lang: Raw language code string
        
    Returns:
        Standardized 2-letter language code if matched, else original lowecased string
    """
    if not lang:
        return 'unknown'
        
    clean_lang = lang.lower().strip()
    
    # Direct match in map
    if clean_lang in LANGUAGE_NORMALIZATION_MAP:
        return LANGUAGE_NORMALIZATION_MAP[clean_lang]
        
    # Handle cases like "en-US" -> "en"
    if '-' in clean_lang:
        base = clean_lang.split('-')[0]
        if base in LANGUAGE_NORMALIZATION_MAP:
            return LANGUAGE_NORMALIZATION_MAP[base]
            
    return clean_lang
