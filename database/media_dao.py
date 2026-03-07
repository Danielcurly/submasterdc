#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Media File Data Access Object (DAO)
Responsible for media file related database operations
"""

import json
from typing import List, Optional, Dict


from database.connection import get_db_connection, execute_many
from core.models import MediaFile, SubtitleInfo


class MediaDAO:
    """Media File Data Access Object"""
    
    @staticmethod
    def get_all_media_files() -> List[MediaFile]:
        """
        Get all media files
        
        Returns:
            List of media files
        """
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                "SELECT id, file_path, file_name, file_size, subtitles_json, "
                "has_translated, embedded_tracks_json, updated_at FROM media_files ORDER BY file_name"
            )
            
            media_files = []
            for row in cursor.fetchall():
                try:
                    media = MediaFile(
                        id=row[0],
                        file_path=row[1],
                        file_name=row[2],
                        file_size=row[3],
                        subtitles=MediaDAO._parse_subtitles(row[4]),
                        has_translated=bool(row[5]),
                        embedded_tracks=json.loads(row[6]) if row[6] else [],
                        updated_at=row[7]
                    )
                    media_files.append(media)
                except Exception as e:
                    print(f"[MediaDAO] Failed to parse media file {row[0]}: {e}")
                    continue
            
            return media_files
        finally:
            conn.close()
    
    
    @staticmethod
    def get_media_by_path(file_path: str) -> Optional[MediaFile]:
        """
        Get media file by file path
        
        Args:
            file_path: File path
        
        Returns:
            MediaFile object, or None if not found
        """
        conn = get_db_connection()
        try:
            result = conn.execute(
                "SELECT id, file_path, file_name, file_size, subtitles_json, "
                "has_translated, embedded_tracks_json, updated_at FROM media_files WHERE file_path=?",
                (file_path,)
            ).fetchone()
            
            if not result:
                return None
            
            return MediaFile(
                id=result[0],
                file_path=result[1],
                file_name=result[2],
                file_size=result[3],
                subtitles=MediaDAO._parse_subtitles(result[4]),
                has_translated=bool(result[5]),
                embedded_tracks=json.loads(result[6]) if result[6] else [],
                updated_at=result[7]
            )
        finally:
            conn.close()

    @staticmethod
    def get_media_by_path_prefix(path_prefix: str) -> List[MediaFile]:
        """
        Get all media files that start with specific path prefix
        
        Args:
            path_prefix: Directory path prefix
            
        Returns:
            List of matching MediaFile objects
        """
        conn = get_db_connection()
        try:
            # We use LIKE with a wildcard to match files under the given directory
            prefix_pattern = f"{path_prefix}%"
            cursor = conn.execute(
                "SELECT id, file_path, file_name, file_size, subtitles_json, "
                "has_translated, embedded_tracks_json, updated_at FROM media_files WHERE file_path LIKE ?",
                (prefix_pattern,)
            )
            
            media_files = []
            for row in cursor.fetchall():
                try:
                    media = MediaFile(
                        id=row[0],
                        file_path=row[1],
                        file_name=row[2],
                        file_size=row[3],
                        subtitles=MediaDAO._parse_subtitles(row[4]),
                        has_translated=bool(row[5]),
                        embedded_tracks=json.loads(row[6]) if row[6] else [],
                        updated_at=row[7]
                    )
                    media_files.append(media)
                except Exception as e:
                    print(f"[MediaDAO] Failed to parse media file {row[0]}: {e}")
                    continue
            
            return media_files
        finally:
            conn.close()
    
    @staticmethod
    def add_or_update_media_file(
        file_path: str,
        file_name: str,
        file_size: int,
        subtitles: List[SubtitleInfo],
        has_translated: bool = False,
        embedded_tracks: List[Dict] = None
    ):
        """
        Add or update media file
        
        Args:
            file_path: File path
            file_name: File name
            file_size: File size
            subtitles: Subtitles list
            has_translated: Whether it has translations
        """
        conn = get_db_connection()
        try:
            subtitles_json = json.dumps(
                [s.to_dict() for s in subtitles],
                ensure_ascii=False
            )
            
            conn.execute(
                "INSERT OR REPLACE INTO media_files "
                "(file_path, file_name, file_size, subtitles_json, has_translated, embedded_tracks_json, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (file_path, file_name, file_size, subtitles_json, int(has_translated), json.dumps(embedded_tracks or []))
            )
            conn.commit()
        except Exception as e:
            print(f"[MediaDAO] Failed to add/update media file: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    @staticmethod
    def batch_add_or_update_media_files(media_files: List[tuple]):
        """
        Batch add or update media files
        
        Args:
            media_files: List of tuples [(file_path, file_name, file_size, subtitles_json, has_translated, embedded_tracks_json), ...]
        """
        try:
            execute_many(
                "INSERT OR REPLACE INTO media_files "
                "(file_path, file_name, file_size, subtitles_json, has_translated, embedded_tracks_json, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                media_files
            )
        except Exception as e:
            print(f"[MediaDAO] Failed to batch add/update media files: {e}")
            raise
    
    @staticmethod
    def update_media_subtitles(
        file_path: str,
        subtitles: List[SubtitleInfo],
        has_translated: bool
    ):
        """
        Update media file subtitle information
        
        Args:
            file_path: File path
            subtitles: Subtitles list
            has_translated: Whether it has translations
        """
        conn = get_db_connection()
        try:
            subtitles_json = json.dumps(
                [s.to_dict() for s in subtitles],
                ensure_ascii=False
            )
            
            conn.execute(
                "UPDATE media_files SET subtitles_json=?, has_translated=?, "
                "updated_at=CURRENT_TIMESTAMP WHERE file_path=?",
                (subtitles_json, int(has_translated), file_path)
            )
            conn.commit()
        except Exception as e:
            print(f"[MediaDAO] Failed to update media subtitles: {e}")
            conn.rollback()
        finally:
            conn.close()

    @staticmethod
    def update_embedded_tracks(file_path: str, embedded_tracks: List[Dict]):
        """
        Update the embedded tracks information for a media file
        
        Args:
            file_path: The file path of the media
            embedded_tracks: List of dictionaries containing track info (index, codec, lang)
        """
        conn = get_db_connection()
        try:
            conn.execute(
                "UPDATE media_files SET embedded_tracks_json=?, "
                "updated_at=CURRENT_TIMESTAMP WHERE file_path=?",
                (json.dumps(embedded_tracks, ensure_ascii=False), file_path)
            )
            conn.commit()
        except Exception as e:
            print(f"[MediaDAO] Failed to update embedded tracks: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    @staticmethod
    def get_media_count_for_library(library_path: str) -> int:
        """Get the number of media files matching this library path prefix"""
        conn = get_db_connection()
        try:
            import os
            # Ensure path ends with slash for exact prefix matching of dir
            norm_path = os.path.normpath(library_path)
            if os.name == 'nt' and not norm_path.endswith('\\'):
                norm_path += '\\'
            elif os.name != 'nt' and not norm_path.endswith('/'):
                norm_path += '/'
                
            cursor = conn.execute(
                "SELECT COUNT(*) FROM media_files WHERE file_path LIKE ?", 
                (f"{norm_path}%",)
            )
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"[MediaDAO] Failed to get media count for library {library_path}: {e}")
            return 0
        finally:
            conn.close()

    @staticmethod
    def delete_media_file(file_path: str):
        """
        Delete media file record
        
        Args:
            file_path: File path
        """
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM media_files WHERE file_path=?", (file_path,))
            conn.commit()
        except Exception as e:
            print(f"[MediaDAO] Failed to delete media file: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    @staticmethod
    def get_media_count() -> int:
        """
        Get total number of media files
        
        Returns:
            Number of files
        """
        conn = get_db_connection()
        try:
            result = conn.execute("SELECT COUNT(*) FROM media_files").fetchone()
            return result[0] if result else 0
        finally:
            conn.close()
    
    @staticmethod
    def count_app_generated_subtitles() -> int:
        """
        Count total number of app-generated subtitle entries across all media files.
        More efficient than loading all MediaFile objects — only reads subtitles_json column.
        
        Returns:
            Total count of subtitles with is_app_generated=True
        """
        conn = get_db_connection()
        try:
            cursor = conn.execute("SELECT subtitles_json FROM media_files")
            count = 0
            for row in cursor.fetchall():
                try:
                    subs = json.loads(row[0]) if row[0] else []
                    count += sum(1 for s in subs if s.get('is_app_generated', False))
                except (json.JSONDecodeError, TypeError):
                    continue
            return count
        except Exception as e:
            print(f"[MediaDAO] Failed to count app-generated subtitles: {e}")
            return 0
        finally:
            conn.close()
            
    @staticmethod
    def get_library_subtitle_stats(target_languages: List[str], libraries: List) -> Dict:
        """
        Calculates library-wide subtitle statistics.
        
        Args:
            target_languages: List of language codes to match embedded tracks against.
            libraries: List of configured LibraryFolders to map relative paths.
            
        Returns:
            Dictionary with counts and detailed ASS metadata.
        """
        import os
        from typing import Any
        
        stats: Dict[str, Any] = {
            'generated_subs': 0,
            'embedded_subs': 0,
            'existing_ass': 0,
            'existing_ass_list': []
        }
        
        target_langs_lower = [l.lower() for l in target_languages]
        
        conn = get_db_connection()
        try:
            cursor = conn.execute("SELECT file_path, subtitles_json, embedded_tracks_json FROM media_files")
            for row in cursor.fetchall():
                file_path, subs_str, embedded_str = row
                
                # Parse JSON fields safely
                subs = []
                embedded = []
                try:
                    if subs_str: subs = json.loads(subs_str)
                    if embedded_str: embedded = json.loads(embedded_str)
                except:
                    pass
                
                # Check generated and existing ASS subtitles
                for sub in subs:
                    is_generated = sub.get('is_app_generated', False)
                    if is_generated:
                        stats['generated_subs'] += 1
                    else:
                        sub_path = sub.get('path', '')
                        if sub_path.lower().endswith('.ass'):
                            stats['existing_ass'] += 1
                            
                            # Find matching library to build relative paths
                            lib_name = "Unknown"
                            rel_dir = ""
                            sub_file_name = os.path.basename(sub_path)
                            
                            for lib in libraries:
                                lib_path_norm = os.path.normpath(lib.path) + os.sep
                                file_path_norm = os.path.normpath(file_path)
                                
                                if file_path_norm.startswith(lib_path_norm) or file_path_norm == os.path.normpath(lib.path):
                                    lib_name = lib.name
                                    try:
                                        rel_path_full = os.path.relpath(sub_path, lib.path)
                                        rel_dir = os.path.dirname(rel_path_full)
                                        if rel_dir == "" or rel_dir == ".":
                                            rel_dir = "/"
                                        else:
                                            rel_dir = "/" + rel_dir.replace("\\", "/").strip("/")
                                    except ValueError:
                                        pass
                                    break
                            
                            stats['existing_ass_list'].append({
                                'library_name': lib_name,
                                'rel_path': rel_dir,
                                'file_name': sub_file_name
                            })
                
                # Check embedded tracks
                for track in embedded:
                    lang = track.get('lang')
                    if lang and lang.lower() in target_langs_lower:
                        stats['embedded_subs'] += 1

            return stats
        except Exception as e:
            print(f"[MediaDAO] Failed to calculate subtitle stats: {e}")
            return stats
        finally:
            conn.close()
    
    @staticmethod
    def _parse_subtitles(subtitles_json: str) -> List[SubtitleInfo]:
        """
        Parse subtitles JSON
        
        Args:
            subtitles_json: JSON string
        
        Returns:
            List of subtitle information
        """
        try:
            data = json.loads(subtitles_json)
            return [SubtitleInfo.from_dict(s) for s in data]
        except Exception as e:
            print(f"[MediaDAO] Failed to parse subtitles JSON: {e}")
            return []