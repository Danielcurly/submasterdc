#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Language Detection Tool
Detects language type based on subtitle content
"""

import re


def detect_language_from_subtitle(srt_path: str) -> str:
    """
    Detect language from subtitle content
    
    Args:
        srt_path: SRT file path
    
    Returns:
        Language code (zh/chs/cht/en/ja/ko/unknown)
    """
    try:
        with open(srt_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_content = f.read(4096)  # Only read first 4KB
        
        # Remove timeline and indices
        content = re.sub(
            r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}',
            '',
            raw_content
        )
        content = re.sub(r'^\d+$', '', content, flags=re.MULTILINE)
        
        # Character statistics
        total_chars = len(re.sub(r'\s+', '', content))
        if total_chars < 50:
            return 'unknown'
        
        # Language characteristic characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', content))
        hiragana_chars = len(re.findall(r'[\u3040-\u309f]', content))
        katakana_chars = len(re.findall(r'[\u30a0-\u30ff]', content))
        hangul_chars = len(re.findall(r'[\uac00-\ud7af]', content))
        
        # Traditional Chinese markers
        traditional_markers = [
            '臺', '灣', '繁', '體', '於', '與', 
            '個', '們', '裡', '這', '妳', '臉', 
            '廳', '學', '習'
        ]
        traditional_count = sum(1 for char in traditional_markers if char in content)
        
        # English word statistics
        english_words = re.findall(r'\b[a-zA-Z]{3,}\b', content)
        english_chars = sum(len(word) for word in english_words)
        
        # Determine language
        if hiragana_chars >= 5 or katakana_chars >= 5:
            return 'ja'
        
        if hangul_chars >= 10:
            return 'ko'
        
        if chinese_chars >= 10:
            # Differentiate simplified/traditional
            if traditional_count >= 3 and traditional_count / chinese_chars >= 0.2:
                return 'cht'
            return 'chs'
        
        if total_chars > 0 and english_chars / total_chars >= 0.5:
            return 'en'
        
        return 'unknown'
        
    except Exception as e:
        print(f"[LangDetection] Failed to detect language for {srt_path}: {e}")
        return 'unknown'


def detect_language_from_filename(filename: str) -> str:
    """
    Detect language from filename
    
    Args:
        filename: Filename
    
    Returns:
        Language code (zh/chs/cht/en/ja/ko/unknown)
    """
    filename_lower = filename.lower()
    
    # Check common language codes
    lang_codes = {
        'chs': 'chs',
        'cht': 'cht',
        'eng': 'en',
        'jpn': 'ja',
        'kor': 'ko',
        'zh': 'chs',
        'en': 'en',
        'ja': 'ja',
        'ko': 'ko',
    }
    
    for code, lang in lang_codes.items():
        # Check .code. or .code suffix
        if f".{code}." in filename_lower or filename_lower.endswith(f".{code}"):
            return lang
    
    return 'unknown'


def detect_language_combined(
    srt_path: str,
    filename: str
) -> tuple[str, str]:
    """
    Comprehensive language detection (filename + content)
    
    Args:
        srt_path: SRT file path
        filename: Filename
    
    Returns:
        (language code, tag)
    """
    # Try filename detection first
    lang_from_filename = detect_language_from_filename(filename)
    
    if lang_from_filename != 'unknown':
        return lang_from_filename, get_language_tag(lang_from_filename)
    
    # Filename detection failed, try content detection
    lang_from_content = detect_language_from_subtitle(srt_path)
    return lang_from_content, get_language_tag(lang_from_content)


def get_language_tag(lang_code: str) -> str:
    """
    Get language tag
    
    Args:
        lang_code: Language code
    
    Returns:
        Language tag (English)
    """
    lang_map = {
        'chs': 'Simplified Chinese',
        'cht': 'Traditional Chinese',
        'zh': 'Chinese',
        'en': 'English',
        'eng': 'English',
        'ja': 'Japanese',
        'jpn': 'Japanese',
        'ko': 'Korean',
        'kor': 'Korean',
        'fr': 'French',
        'de': 'German',
        'ru': 'Russian',
        'es': 'Spanish',
        'unknown': 'Unknown'
    }
    return lang_map.get(lang_code.lower(), 'Unknown')