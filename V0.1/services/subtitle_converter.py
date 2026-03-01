#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Subtitle Format Converter
Supports multiple subtitle formats: SRT, ASS, VTT, SSA, SUB
"""

import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import timedelta


@dataclass
class SubtitleEntry:
    """General subtitle entry"""
    index: int
    start_ms: int  # Start time in ms
    end_ms: int    # End time in ms
    text: str
    
    def duration_ms(self) -> int:
        """Get duration in ms"""
        return self.end_ms - self.start_ms


class SubtitleConverter:
    """Subtitle format converter"""
    
    @staticmethod
    def parse_srt_time(time_str: str) -> int:
        """
        Parse SRT time format to milliseconds
        Format: HH:MM:SS,mmm
        """
        match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str)
        if not match:
            raise ValueError(f"Invalid SRT time format: {time_str}")
        
        hours, minutes, seconds, milliseconds = map(int, match.groups())
        return (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
    
    @staticmethod
    def format_srt_time(ms: int) -> str:
        """
        Format milliseconds to SRT time
        Format: HH:MM:SS,mmm
        """
        if ms < 0:
            ms = 0
        
        hours = ms // 3600000
        ms %= 3600000
        minutes = ms // 60000
        ms %= 60000
        seconds = ms // 1000
        milliseconds = ms % 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    @staticmethod
    def format_vtt_time(ms: int) -> str:
        """
        Format milliseconds to VTT time
        Format: HH:MM:SS.mmm
        """
        srt_time = SubtitleConverter.format_srt_time(ms)
        return srt_time.replace(',', '.')
    
    @staticmethod
    def format_ass_time(ms: int) -> str:
        """
        Format milliseconds to ASS/SSA time
        Format: H:MM:SS.cc (centiseconds)
        """
        if ms < 0:
            ms = 0
        
        hours = ms // 3600000
        ms %= 3600000
        minutes = ms // 60000
        ms %= 60000
        seconds = ms // 1000
        centiseconds = (ms % 1000) // 10
        
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
    
    @staticmethod
    def parse_srt(content: str) -> List[SubtitleEntry]:
        """Parse SRT format"""
        entries = []
        blocks = content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            try:
                index = int(lines[0].strip())
                timecode = lines[1].strip()
                text = '\n'.join(lines[2:]).strip()
                
                # Parse timeline
                match = re.match(r'([\d:,]+)\s*-->\s*([\d:,]+)', timecode)
                if not match:
                    continue
                
                start_ms = SubtitleConverter.parse_srt_time(match.group(1))
                end_ms = SubtitleConverter.parse_srt_time(match.group(2))
                
                entries.append(SubtitleEntry(
                    index=index,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=text
                ))
            except (ValueError, IndexError):
                continue
        
        return entries
    
    @staticmethod
    def to_srt(entries: List[SubtitleEntry]) -> str:
        """
        Convert to SRT format
        
        Example:
        1
        00:00:01,000 --> 00:00:03,000
        Hello, world!
        """
        lines = []
        for entry in entries:
            start = SubtitleConverter.format_srt_time(entry.start_ms)
            end = SubtitleConverter.format_srt_time(entry.end_ms)
            
            lines.append(f"{entry.index}")
            lines.append(f"{start} --> {end}")
            lines.append(entry.text)
            lines.append("")  # Empty line separator
        
        return '\n'.join(lines)
    
    @staticmethod
    def to_vtt(entries: List[SubtitleEntry]) -> str:
        """
        Convert to WebVTT format
        
        Example:
        WEBVTT
        
        1
        00:00:01.000 --> 00:00:03.000
        Hello, world!
        """
        lines = ["WEBVTT", ""]
        
        for entry in entries:
            start = SubtitleConverter.format_vtt_time(entry.start_ms)
            end = SubtitleConverter.format_vtt_time(entry.end_ms)
            
            lines.append(f"{entry.index}")
            lines.append(f"{start} --> {end}")
            lines.append(entry.text)
            lines.append("")
        
        return '\n'.join(lines)
    
    @staticmethod
    def to_ass(entries: List[SubtitleEntry], 
               style_name: str = "Default",
               font_name: str = "Arial",
               font_size: int = 20) -> str:
        """
        Convert to ASS (Advanced SubStation Alpha) format
        
        ASS supports rich styles and effects, good compatibility
        """
        # ASS Header
        header = f"""[Script Info]
; Script generated by NAS Subtitle Manager
Title: Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {style_name},{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        lines = [header]
        
        for entry in entries:
            start = SubtitleConverter.format_ass_time(entry.start_ms)
            end = SubtitleConverter.format_ass_time(entry.end_ms)
            
            # Handle newlines (ASS uses \N)
            text = entry.text.replace('\n', '\\N')
            
            lines.append(f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def to_ssa(entries: List[SubtitleEntry],
               style_name: str = "Default",
               font_name: str = "Arial",
               font_size: int = 20) -> str:
        """
        Convert to SSA (SubStation Alpha) format
        
        SSA is the predecessor of ASS, better compatibility but fewer features
        """
        # SSA Header
        header = f"""[Script Info]
; Script generated by NAS Subtitle Manager
Title: Subtitles
ScriptType: v4.00
Collisions: Normal
PlayResX: 1920
PlayResY: 1080
Timer: 100.0000

[V4 Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, TertiaryColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, AlphaLevel, Encoding
Style: {style_name},{font_name},{font_size},16777215,65535,65535,-2147483640,0,0,1,2,1,2,10,10,10,0,1

[Events]
Format: Marked, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        lines = [header]
        
        for entry in entries:
            start = SubtitleConverter.format_ass_time(entry.start_ms)
            end = SubtitleConverter.format_ass_time(entry.end_ms)
            
            # Handle newlines (SSA also uses \N)
            text = entry.text.replace('\n', '\\N')
            
            lines.append(f"Dialogue: Marked=0,{start},{end},{style_name},,0,0,0,,{text}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def to_sub(entries: List[SubtitleEntry]) -> str:
        """
        Convert to SUB (MicroDVD) format
        
        Example:
        {100}{200}Hello, world!
        
        Note: SUB uses frames instead of time, assuming 25fps here
        """
        fps = 25  # Assume 25 frames per second
        lines = []
        
        for entry in entries:
            start_frame = int(entry.start_ms * fps / 1000)
            end_frame = int(entry.end_ms * fps / 1000)
            
            # Handle newlines (SUB uses |)
            text = entry.text.replace('\n', '|')
            
            lines.append(f"{{{start_frame}}}{{{end_frame}}}{text}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def convert_file(input_path: str, 
                    output_format: str,
                    output_path: Optional[str] = None) -> str:
        """
        Convert subtitle file format
        """
        # Read input file
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Parse to general format
        entries = SubtitleConverter.parse_srt(content)
        
        if not entries:
            raise ValueError("Failed to parse subtitle file or file is empty")
        
        # Convert to target format
        output_format = output_format.lower()
        if output_format == 'srt':
            output_content = SubtitleConverter.to_srt(entries)
        elif output_format == 'vtt':
            output_content = SubtitleConverter.to_vtt(entries)
        elif output_format == 'ass':
            output_content = SubtitleConverter.to_ass(entries)
        elif output_format == 'ssa':
            output_content = SubtitleConverter.to_ssa(entries)
        elif output_format == 'sub':
            output_content = SubtitleConverter.to_sub(entries)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
        
        # Generate output path
        if output_path is None:
            input_file = Path(input_path)
            output_path = str(input_file.parent / f"{input_file.stem}.{output_format}")
        
        # Write output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        return output_path
    
    @staticmethod
    def convert_to_bilingual_ass(primary_srt_path: str, secondary_srt_path: str, output_path: str) -> str:
        """Create a bilingual ASS file using style configurations from ejemplo.ass"""
        with open(primary_srt_path, 'r', encoding='utf-8', errors='ignore') as f:
            p_content = f.read()
        with open(secondary_srt_path, 'r', encoding='utf-8', errors='ignore') as f:
            s_content = f.read()
            
        p_entries = SubtitleConverter.parse_srt(p_content)
        s_entries = SubtitleConverter.parse_srt(s_content)
        
        # ASS Header matching ejemplo.ass
        header = """[Script Info]
; Script generated by NAS Subtitle Manager (Bilingual)
Title: Bilingual Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,22,&H00DFDFDF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,5,5,5,134
Style: Eng,Microsoft YaHei,11,&H00027CCF,&H00000000,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,5,5,5,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""

        lines = [header]
        sec_map = {e.index: e.text.replace('\\n', ' ').replace('\n', ' ') for e in s_entries}
        
        for p in p_entries:
            start = SubtitleConverter.format_ass_time(p.start_ms)
            end = SubtitleConverter.format_ass_time(p.end_ms)
            p_text = p.text.replace('\n', '\\N')
            s_text = sec_map.get(p.index, "")
            
            if s_text:
                text = f"{p_text}\\N{{\\rEng}}{s_text}"
            else:
                text = p_text
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return output_path

    @staticmethod
    def convert_to_bilingual_srt(primary_srt_path: str, secondary_srt_path: str, output_path: str) -> str:
        """Create a bilingual SRT file using HTML font tags"""
        with open(primary_srt_path, 'r', encoding='utf-8', errors='ignore') as f:
            p_content = f.read()
        with open(secondary_srt_path, 'r', encoding='utf-8', errors='ignore') as f:
            s_content = f.read()
            
        p_entries = SubtitleConverter.parse_srt(p_content)
        s_entries = SubtitleConverter.parse_srt(s_content)
        sec_map = {e.index: e.text.replace('\\n', ' ').replace('\n', ' ') for e in s_entries}
        
        lines = []
        for p in p_entries:
            start = SubtitleConverter.format_srt_time(p.start_ms)
            end = SubtitleConverter.format_srt_time(p.end_ms)
            p_text = p.text
            s_text = sec_map.get(p.index, "")
            
            lines.append(f"{p.index}")
            lines.append(f"{start} --> {end}")
            if s_text:
                lines.append(f"{p_text}\n<font size=\"12\">{s_text}</font>")
            else:
                lines.append(p_text)
            lines.append("")
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        return output_path
    
    @staticmethod
    def convert_to_all_formats(input_path: str) -> Dict[str, str]:
        """
        Convert subtitle to all supported formats
        """
        formats = ['srt', 'vtt', 'ass', 'ssa', 'sub']
        results = {}
        
        for fmt in formats:
            try:
                output_path = SubtitleConverter.convert_file(input_path, fmt)
                results[fmt] = output_path
            except Exception as e:
                print(f"Failed to convert to {fmt} format: {e}")
        
        return results


# ============================================================================
# CLI Tool
# ============================================================================
def main():
    """Command line tool"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
Subtitle Format Converter

Usage:
  python subtitle_converter.py convert <input.srt> <format>     # Convert to specified format
  python subtitle_converter.py convert-all <input.srt>          # Convert to all formats
  python subtitle_converter.py formats                          # Show supported formats

Supported formats:
  - srt  : SubRip (Most universal)
  - vtt  : WebVTT (Web players)
  - ass  : Advanced SubStation Alpha (Rich Styles)
  - ssa  : SubStation Alpha (Good compatibility)
  - sub  : MicroDVD (Legacy players)

Example:
  python subtitle_converter.py convert movie.srt vtt
  python subtitle_converter.py convert movie.zh.srt ass
  python subtitle_converter.py convert-all movie.srt
        """)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'formats':
        print("\nSupported subtitle formats:\n")
        print("1. SRT  - SubRip")
        print("   - Most universal format")
        print("   - Supported by almost all players")
        print("   - Recommended for most scenarios")
        print()
        print("2. VTT  - WebVTT")
        print("   - Web video standard format")
        print("   - For HTML5 players")
        print("   - Suitable for online platforms")
        print()
        print("3. ASS  - Advanced SubStation Alpha")
        print("   - Supports rich styles and effects")
        print("   - Common for Anime fansubs")
        print("   - Compatibility: VLC, MPC-HC, PotPlayer")
        print()
        print("4. SSA  - SubStation Alpha")
        print("   - Predecessor of ASS")
        print("   - Better compatibility but fewer features")
        print("   - Suitable for legacy players")
        print()
        print("5. SUB  - MicroDVD")
        print("   - Based on frame counts instead of time")
        print("   - Supported by legacy DVD players")
        print("   - Not recommended for new projects")
        print()
    
    elif command == 'convert':
        if len(sys.argv) < 4:
            print("Error: Missing parameters")
            print("Usage: python subtitle_converter.py convert <input.srt> <format>")
            sys.exit(1)
        
        input_path = sys.argv[2]
        output_format = sys.argv[3]
        
        try:
            output_path = SubtitleConverter.convert_file(input_path, output_format)
            print(f"✅ Conversion successful: {output_path}")
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            sys.exit(1)
    
    elif command == 'convert-all':
        if len(sys.argv) < 3:
            print("Error: Missing input file")
            print("Usage: python subtitle_converter.py convert-all <input.srt>")
            sys.exit(1)
        
        input_path = sys.argv[2]
        
        print(f"Converting {Path(input_path).name} to all formats...\n")
        
        results = SubtitleConverter.convert_to_all_formats(input_path)
        
        print("Conversion Results:")
        for fmt, path in results.items():
            print(f"  ✅ {fmt.upper()}: {Path(path).name}")
        
        print(f"\nGenerated {len(results)} files in total")
    
    else:
        print(f"Error: Unknown command '{command}'")
        sys.exit(1)


if __name__ == "__main__":
    main()