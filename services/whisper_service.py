#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whisper Subtitle Extraction Service
Responsible for extracting subtitles from video
"""

from pathlib import Path
from typing import Optional, Callable
import subprocess
import time
import numpy as np
from faster_whisper import WhisperModel

from core.models import WhisperConfig, VADParameters, SubtitleEntry
from utils.format_utils import format_timestamp


class WhisperService:
    """Whisper Subtitle Extraction Service"""
    
    def __init__(
        self,
        config: WhisperConfig,
        vad_params: VADParameters,
        model_dir: str = "./data/models"
    ):
        """
        Initialize Whisper service
        
        Args:
            config: Whisper configuration
            vad_params: VAD parameters
            model_dir: Directory to store models
        """
        self.config = config
        self.vad_params = vad_params
        self.model_dir = model_dir
        self.model: Optional[WhisperModel] = None
        self.last_activity_time = time.time()
    
    def load_model(self):
        """Load Whisper model"""
        if self.model is not None:
            return
        
        try:
            self.model = WhisperModel(
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
                cpu_threads=self.config.cpu_threads,
                download_root=self.model_dir
            )
            print(f"[WhisperService] Model loaded: {self.config.model_size} (CPU threads: {self.config.cpu_threads})")
            self.last_activity_time = time.time()
        except Exception as e:
            print(f"[WhisperService] Failed to load model: {e}")
            raise
            
    def _detect_language_at_offset(self, video_path: str, offset: int) -> Optional[str]:
        """Detect language by sampling audio at a specific offset (N100 optimized)"""
        from services.embedded_extractor import FFMPEG_PATH
        
        try:
            # Extract 30 seconds of audio buffer starting at offset
            cmd = [
                FFMPEG_PATH,
                '-ss', str(offset),
                '-t', '30',
                '-i', video_path,
                '-f', 's16le',
                '-acodec', 'pcm_s16le',
                '-ac', '1',
                '-ar', '16000',
                '-'
            ]
            
            # Run FFmpeg and capture stdout
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            
            if not stdout or len(stdout) < 32000: # Need at least 1 second
                return None
                
            # Convert to float32 ndarray (16kHz)
            audio_array = np.frombuffer(stdout, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Use faster-whisper to transcribe a tiny bit just to get language info
            # We use beam_size=1 and no results just for info
            _, info = self.model.transcribe(audio_array, beam_size=1, duration=30)
            
            return info.language
        except Exception as e:
            print(f"[WhisperService] Language sampling at offset {offset} failed: {e}")
            return None
    
    def extract_subtitle(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Extract subtitles from video
        
        Args:
            video_path: Video file path
            output_path: Output SRT file path (default: same name .srt)
            progress_callback: Progress callback function (current, total, message)
        
        Returns:
            Generated SRT file path
        """
        # Ensure model is loaded
        if self.model is None:
            self.load_model()
        self.last_activity_time = time.time()
        
        # Determine output path
        if output_path is None:
            output_path = str(Path(video_path).with_suffix('.srt'))
        
        # Update progress
        if progress_callback:
            progress_callback(5, 100, "Starting subtitle extraction...")
        
        # Prepare transcription parameters (Optimized for CPU/N100)
        transcribe_params = {
            'audio': video_path,
            'beam_size': 3,
            'vad_filter': True,
            'vad_parameters': self.vad_params.to_dict(),
            'word_timestamps': False,
            'condition_on_previous_text': True,
            'temperature': [0.0, 0.4],
        }
        
        # Specify language if not auto-detect
        if self.config.source_language != 'auto':
            transcribe_params['language'] = self.config.source_language
        else:
            # Multi-point language detection (Voting system)
            from services.embedded_extractor import get_video_duration
            duration = get_video_duration(video_path)
            
            # Points to sample: 0s, 5m (300s), 10m (600s)
            points = [0]
            if duration > 300: points.append(300)
            if duration > 600: points.append(600)
            
            if progress_callback:
                progress_callback(8, 100, f"Performing multi-point language detection ({len(points)} samples)...")
            
            results = []
            for p in points:
                det = self._detect_language_at_offset(video_path, p)
                if det:
                    results.append(det)
                    if progress_callback:
                        progress_callback(8 + len(results)*2, 100, f"Sample at {p}s: {det}")

            if not results:
                 raise Exception("Could not detect language from any sample point")
            
            # Voting
            from collections import Counter
            counts = Counter(results)
            # Check if there's a winner or all are different
            top_langs = counts.most_common()
            if len(top_langs) > 1 and top_langs[0][1] == top_langs[1][1]:
                # Tie or all different
                if len(results) >= 2:
                    raise Exception(f"Language detection conflict: samples returned different languages {results}")
            
            winner = top_langs[0][0]
            transcribe_params['language'] = winner
            
            if progress_callback:
                from utils.format_utils import get_lang_name
                lang_name = get_lang_name(winner)
                progress_callback(15, 100, f"Detected language: {lang_name} (via voting)")
        
        try:
            # Execute transcription
            segments, info = self.model.transcribe(**transcribe_params)
            
            # Collect entries
            entries = []
            idx = 0
            for seg in segments:
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Whisper extraction cancelled by user")
                
                idx += 1
                entries.append(SubtitleEntry(
                    index=idx,
                    start_ms=int(seg.start * 1000),
                    end_ms=int(seg.end * 1000),
                    text=seg.text.strip()
                ))
                
                # Update progress
                if progress_callback and idx % 10 == 0:
                    progress = 15 + min(35, int(idx / 300 * 35))
                    progress_callback(progress, 100, f"Transcribed {idx} lines")
            
            # Save using centralized logic
            from services.subtitle_converter import SubtitleConverter
            SubtitleConverter.save_srt(entries, output_path)
            
            # Complete
            if progress_callback:
                progress_callback(50, 100, f"Subtitle extraction complete ({idx} lines)")
            
            self.last_activity_time = time.time()
            return output_path
        
        except Exception as e:
            print(f"[WhisperService] Extraction failed: {e}")
            self.last_activity_time = time.time()
            raise
    
    def check_idle_timeout(self, timeout_seconds: int = 600):
        """Check if model has been idle and unload if necessary"""
        if self.model is None:
            return
            
        idle_time = time.time() - self.last_activity_time
        if idle_time > timeout_seconds:
            print(f"[WhisperService] Model idle for {int(idle_time)}s, unloading to free memory...")
            self.unload_model()
    
    def unload_model(self):
        """Unload model (free memory)"""
        if self.model is not None:
            del self.model
            self.model = None
            print("[WhisperService] Model unloaded")


# ============================================================================
# Quick Functions
# ============================================================================

def extract_subtitle_from_video(
    video_path: str,
    config: WhisperConfig,
    vad_params: VADParameters,
    output_path: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None
) -> str:
    """
    Extract subtitles from video (quick function)
    
    Args:
        video_path: Video file path
        config: Whisper configuration
        vad_params: VAD parameters
        output_path: Output path (optional)
        progress_callback: Progress callback
    
    Returns:
        SRT file path
    """
    service = WhisperService(config, vad_params)
    return service.extract_subtitle(video_path, output_path, progress_callback, is_cancelled)