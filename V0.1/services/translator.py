#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Subtitle Translation Module (Refactored)
Main improvements:
1. Forced structured output using JSON
2. Intelligent batching strategy (single translation for short videos, scene-based for long)
3. Enhanced error handling (no longer silent failure)
4. Supports translation quality checking and retry
"""

import json
import time
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from openai import OpenAI
from dataclasses import dataclass


@dataclass
class TranslationConfig:
    """Translation configuration"""
    api_key: str
    base_url: str
    model_name: str
    target_language: str
    source_language: str = 'auto'
    max_lines_per_batch: int = 500  # Maximum lines per translation batch
    max_retries: int = 3
    timeout: int = 180


class SubtitleEntry:
    """Subtitle entry"""
    def __init__(self, index: str, timecode: str, text: str):
        self.index = index
        self.timecode = timecode
        self.text = text
    
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


class TranslationError(Exception):
    """Base class for translation errors"""
    pass


class APIError(TranslationError):
    """API call error"""
    pass


class ParseError(TranslationError):
    """Parsing error"""
    pass


class SubtitleTranslator:
    """Subtitle translator"""
    
    # Language name mapping
    LANG_NAMES = {
        'zh': 'Chinese (Simplified)',
        'en': 'English',
        'ja': 'Japanese',
        'ko': 'Korean',
        'fr': 'French',
        'de': 'German',
        'ru': 'Russian',
        'es': 'Spanish'
    }
    
    def __init__(self, config: TranslationConfig, progress_callback=None):
        """
        Initialize translator
        
        Args:
            config: Translation configuration
            progress_callback: Progress callback function (current, total, message)
        """
        self.config = config
        self.progress_callback = progress_callback
        self.total_errors = 0
        self.MAX_TOTAL_ERRORS = 10  # Maximum errors allowed for a single task
        
        # Parse fallback configurations
        api_keys = [k.strip() for k in config.api_key.split(',')] if config.api_key else []
        model_names = [m.strip() for m in config.model_name.split(',')] if config.model_name else []
        base_urls = [u.strip() for u in config.base_url.split(',')] if config.base_url else []
        
        if not api_keys: api_keys = [""]
        if not model_names: model_names = [""]
        if not base_urls: base_urls = [""]
        
        max_configs = max(len(api_keys), len(model_names), len(base_urls))
        self.fallback_configs = []
        for i in range(max_configs):
            key = api_keys[i % len(api_keys)]
            model = model_names[i % len(model_names)]
            url = base_urls[i % len(base_urls)]
            
            if "ollama" in url.lower() and not key:
                key = "ollama"
                
            self.fallback_configs.append((key, model, url))
            
        self.current_config_idx = 0
        self._init_current_client()
        
    def _init_current_client(self):
        key, model, url = self.fallback_configs[self.current_config_idx]
        self.config.model_name = model
        self.client = OpenAI(api_key=key, base_url=url)
    
    def _update_progress(self, current: int, total: int, message: str):
        """Update progress"""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def _get_target_lang_name(self) -> str:
        """Get target language name"""
        return self.LANG_NAMES.get(
            self.config.target_language, 
            self.config.target_language
        )
    
    def _build_translation_prompt(
        self, 
        entries: List[SubtitleEntry],
        context_before: Optional[str] = None,
        context_after: Optional[str] = None
    ) -> str:
        """
        Build translation prompt (using JSON format)
        
        Args:
            entries: Subtitle entries to translate
            context_before: Preceding context (reference only, do not translate)
            context_after: Succeeding context (reference only, do not translate)
        """
        target_lang = self._get_target_lang_name()
        
        # Build input JSON
        input_json = [
            {"line": i+1, "text": entry.text}
            for i, entry in enumerate(entries)
        ]
        
        # Context hint
        context_hint = ""
        if context_before or context_after:
            context_hint = "\n\nCONTEXT (for reference only, helps understand the flow):"
            if context_before:
                context_hint += f"\nPrevious line: \"{context_before}\""
            if context_after:
                context_hint += f"\nNext line: \"{context_after}\""
        
        prompt = f"""You are a professional subtitle translator. Translate the following dialogue to {target_lang}.

CRITICAL RULES:
1. Output MUST be a valid JSON array with EXACTLY {len(entries)} objects
2. Each object MUST have "line" (number) and "translation" (string) fields
3. Keep translations natural and concise - match the style of {target_lang} subtitles
4. Preserve character names, proper nouns, and technical terms appropriately
5. DO NOT add punctuation at the end unless present in the original
6. DO NOT merge, split, or skip any lines
7. If a line is untranslatable (music notes, sound effects), keep it as-is
8. IMPORTANT: Output COMPLETE JSON array - DO NOT use "..." to abbreviate{context_hint}

INPUT ({len(entries)} lines):
{json.dumps(input_json, ensure_ascii=False, indent=2)}

OUTPUT FORMAT (valid JSON array with ALL {len(entries)} items):
[
  {{"line": 1, "translation": "..."}},
  {{"line": 2, "translation": "..."}},
  {{"line": 3, "translation": "..."}},
  {{"line": {len(entries)}, "translation": "..."}}
]

REMINDER: You MUST include ALL {len(entries)} translations. DO NOT abbreviate with "..." in the actual output.

Now output the COMPLETE JSON array (no extra text, no abbreviations):"""
        
        return prompt
    
    def _parse_translation_response(
        self, 
        response: str, 
        expected_count: int
    ) -> List[str]:
        """
        Parse translation response (JSON format) - Enhanced version
        
        Args:
            response: raw response from API
            expected_count: expected number of translations
        
        Returns:
            List of translated texts
        
        Raises:
            ParseError: If parsing fails
        """
        # Clean response (remove possible markdown code blocks)
        response = response.strip()
        if response.startswith("```"):
            # Remove ```json or ``` at start
            lines = response.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = '\n'.join(lines)
        
        # Remove possible prefix text (like "Sure, here's the translation:")
        if not response.strip().startswith('['):
            # Find first [
            bracket_pos = response.find('[')
            if bracket_pos > 0:
                response = response[bracket_pos:]
        
        # Check for abbreviation symbols "..."
        if '...' in response and '"...' not in response:
            # If ... appears outside of strings (indicating ellipsis), AI returned a truncated format
            raise ParseError(
                f"AI returned truncated format (contains ...), {expected_count} requested translations not fully returned."
                "This usually happens because content is too long for the model - please lower max_lines_per_batch setting."
            )
        
        # Try to parse JSON
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            
            # Try 1: Remove trailing comma (if any)
            if response.rstrip().endswith(',]'):
                response = response.rstrip()[:-2] + ']'
                try:
                    data = json.loads(response)
                except:
                    pass
            
            # Try 2: Check for missing closing bracket
            if not response.rstrip().endswith(']'):
                response = response.rstrip() + ']'
                try:
                    data = json.loads(response)
                except:
                    pass
            
            # If still fails, throw detailed error
            if 'data' not in locals():
                raise ParseError(
                    f"JSON parse error: {e}\n"
                    f"Original response preview: {response[:300]}...\n"
                    f"Response length: {len(response)} chars"
                )
        
        # Validate format
        if not isinstance(data, list):
            raise ParseError(f"Expected JSON array, got: {type(data).__name__}")
        
        if len(data) != expected_count:
            raise ParseError(
                f"Translation count mismatch: Expected {expected_count} items, got {len(data)} items\n"
                f"Note: If AI returned truncated format, lower max_lines_per_batch configuration."
            )
        
        # Extract translations
        translations = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ParseError(f"Item {i+1} is not a dictionary: {item}")
            
            if 'translation' not in item:
                raise ParseError(f"Item {i+1} lacks 'translation' field: {item}")
            
            line_num = item.get('line', i+1)
            if line_num != i+1:
                raise ParseError(
                    f"Item {i+1} has incorrect line number: Expected {i+1}, got {line_num}"
                )
            
            translations.append(str(item['translation']).strip())
        
        return translations
    
    def _translate_batch(
        self,
        entries: List[SubtitleEntry],
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
        retry_count: int = 0
    ) -> List[SubtitleEntry]:
        """
        Translate a batch of subtitles (with retries and intelligent degradation)
        """
        # Intelligent degradation: if batch is too large causing truncations, split in 2
        if len(entries) > 100 and retry_count >= 2:
            print(f"[Intelligent Split] Batch too large ({len(entries)} lines), splitting into 2 sub-batches")
            mid = len(entries) // 2
            batch1 = self._translate_batch(entries[:mid], context_before, entries[mid].text, 0)
            batch2 = self._translate_batch(entries[mid:], entries[mid-1].text, context_after, 0)
            return batch1 + batch2
        
        prompt = self._build_translation_prompt(entries, context_before, context_after)
        
        last_error = None
        for config_idx in range(self.current_config_idx, len(self.fallback_configs)):
            if config_idx > self.current_config_idx:
                self.current_config_idx = config_idx
                self._init_current_client()
                print(f"[Translation] Switched to fallback AI config #{config_idx + 1}")
                
            for attempt in range(self.config.max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.config.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        timeout=self.config.timeout
                    )
                    
                    raw_response = response.choices[0].message.content
                    if raw_response is None:
                        # Some providers return None if filtered or empty
                        finish_reason = response.choices[0].finish_reason
                        raise APIError(f"AI returned empty response. Finish reason: {finish_reason}")
                    
                    raw_response = raw_response.strip()
                    translations = self._parse_translation_response(raw_response, len(entries))
                    
                    # Build translated subtitle entries
                    translated_entries = []
                    for entry, translation in zip(entries, translations):
                        translated_entries.append(
                            SubtitleEntry(
                                index=entry.index,
                                timecode=entry.timecode,
                                text=translation
                            )
                        )
                    
                    return translated_entries
                    
                except ParseError as e:
                    self.total_errors += 1
                    last_error = e
                    error_msg = str(e)
                    
                    # Check for truncated output
                    if "..." in error_msg:
                        print(f"[Translation] Truncation detected, batch size: {len(entries)} lines")
                        # Trigger split - if size is 1 we can't split, just fail
                        if len(entries) > 1:
                            return self._translate_batch(entries, context_before, context_after, retry_count + 99)
                    
                    if self.total_errors >= self.MAX_TOTAL_ERRORS:
                        raise TranslationError(f"TASK_ERROR_LIMIT_REACHED: Too many errors occurred: {e}")

                    if attempt < self.config.max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"[Translation] Parse failed, retrying in {wait_time}s ({attempt+1}/{self.config.max_retries}): {error_msg[:100]}")
                        time.sleep(wait_time)
                    else:
                        raise
                
                except Exception as e:
                    self.total_errors += 1
                    if self.total_errors >= self.MAX_TOTAL_ERRORS:
                        raise TranslationError(f"TASK_ERROR_LIMIT_REACHED: Too many errors occurred: {e}")

                    error_str = str(e).lower()
                    if "429" in error_str or "quota" in error_str or "rate limit" in error_str:
                        print(f"[Translation] Quota error on config #{config_idx + 1}: {e}")
                        last_error = APIError(f"API call failed: {e}")
                        break  # Break attempt loop, try next config
                        
                    last_error = APIError(f"API call failed: {e}")
                    if attempt < self.config.max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"[Translation] API error, retrying in {wait_time}s ({attempt+1}/{self.config.max_retries}): {e}")
                        time.sleep(wait_time)
                    else:
                        raise last_error
                        
        raise TranslationError(f"QUOTA_EXHAUSTED: All fallback AI models/keys exhausted. Last error: {last_error}")
    
    def translate_subtitles(
        self, 
        entries: List[SubtitleEntry]
    ) -> List[SubtitleEntry]:
        """
        Translate subtitles (intelligent segmentation)
        
        Args:
            entries: Original subtitle entries list
        
        Returns:
            Translated subtitle entries list
        """
        if not entries:
            return []
        
        total_lines = len(entries)
        max_batch = self.config.max_lines_per_batch
        
        # Short video: translate all at once
        if total_lines <= max_batch:
            self._update_progress(0, total_lines, f"Starting translation of {total_lines} lines...")
            
            try:
                translated = self._translate_batch(entries)
                self._update_progress(total_lines, total_lines, "Translation complete!")
                return translated
            except Exception as e:
                raise TranslationError(f"Translation failed: {e}")
        
        # Long video: batch translation (retaining context)
        translated_entries = []
        total_batches = (total_lines + max_batch - 1) // max_batch
        
        for i in range(0, total_lines, max_batch):
            batch_num = i // max_batch + 1
            batch = entries[i:i+max_batch]
            
            # Get context
            context_before = entries[i-1].text if i > 0 else None
            context_after = entries[i+max_batch].text if i+max_batch < total_lines else None
            
            self._update_progress(
                i, 
                total_lines, 
                f"Translating batch {batch_num}/{total_batches} ({len(batch)} lines)..."
            )
            
            try:
                translated_batch = self._translate_batch(batch, context_before, context_after)
                translated_entries.extend(translated_batch)
            except Exception as e:
                raise TranslationError(
                    f"Batch {batch_num}/{total_batches} translation failed: {e}"
                )
        
        self._update_progress(total_lines, total_lines, "Translation complete!")
        return translated_entries


# ============================================================================
# Helper Functions
# ============================================================================

def parse_srt_file(srt_path: str) -> List[SubtitleEntry]:
    """
    Parse SRT file
    
    Args:
        srt_path: SRT file path
    
    Returns:
        List of subtitle entries
    """
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    entries = []
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                entries.append(
                    SubtitleEntry(
                        index=lines[0].strip(),
                        timecode=lines[1].strip(),
                        text='\n'.join(lines[2:]).strip()
                    )
                )
            except Exception as e:
                print(f"[Warning] Skipping invalid subtitle block: {e}")
                continue
    
    return entries


def save_srt_file(entries: List[SubtitleEntry], output_path: str):
    """
    Save SRT file
    
    Args:
        entries: Subtitle entries list
        output_path: Output file path
    """
    lines = []
    for entry in entries:
        if not entry.text:
            continue
        lines.append(f"{entry.index}\n{entry.timecode}\n{entry.text}\n")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def translate_srt_file(
    input_path: str,
    config: TranslationConfig,
    output_path: Optional[str] = None,
    progress_callback=None
) -> Tuple[bool, str]:
    """
    Translate SRT file (high-level encapsulation)
    
    Args:
        input_path: input SRT file path
        config: translation config
        output_path: output path (default: original.{target_lang}.srt)
        progress_callback: progress callback
    
    Returns:
        (success flat, message)
    """
    try:
        # Parse original subtitles
        entries = parse_srt_file(input_path)
        if not entries:
            return False, "Subtitle file empty or invalid format"
        
        # Execute translation
        translator = SubtitleTranslator(config, progress_callback)
        translated_entries = translator.translate_subtitles(entries)
        
        # Generate output path
        if output_path is None:
            input_file = Path(input_path)
            output_path = str(
                input_file.parent / 
                f"{input_file.stem}.{config.target_language}.srt"
            )
        
        # Save results
        save_srt_file(translated_entries, output_path)
        
        return True, f"Translation complete, saved to: {output_path}"
        
    except TranslationError as e:
        return False, f"Translation failed: {e}"
    except Exception as e:
        return False, f"Unknown error: {e}"