#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Media File Data Access Object (DAO)
Responsible for media file related database operations
"""

import json
from typing import List, Optional

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
                "has_translated, updated_at FROM media_files ORDER BY file_name"
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
                        updated_at=row[6]
                    )
                    media_files.append(media)
                except Exception as e:
                    print(f"[MediaDAO] Failed to parse media file {row[0]}: {e}")
                    continue
            
            return media_files
        finally:
            conn.close()
    
    @staticmethod
    def get_media_files_filtered(
        has_subtitle: Optional[bool] = None
    ) -> List[MediaFile]:
        """
        Get filtered media files
        
        Args:
            has_subtitle: Whether it has subtitles (None=all, True=has subtitles, False=no subtitles)
        
        Returns:
            List of media files
        """
        all_files = MediaDAO.get_all_media_files()
        
        if has_subtitle is None:
            return all_files
        
        return [f for f in all_files if f.has_subtitle == has_subtitle]
    
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
                "has_translated, updated_at FROM media_files WHERE file_path=?",
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
                updated_at=result[6]
            )
        finally:
            conn.close()
    
    @staticmethod
    def add_or_update_media_file(
        file_path: str,
        file_name: str,
        file_size: int,
        subtitles: List[SubtitleInfo],
        has_translated: bool = False
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
                "(file_path, file_name, file_size, subtitles_json, has_translated, updated_at) "
                "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (file_path, file_name, file_size, subtitles_json, int(has_translated))
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
            media_files: List of tuples [(file_path, file_name, file_size, subtitles_json, has_translated), ...]
        """
        try:
            execute_many(
                "INSERT OR REPLACE INTO media_files "
                "(file_path, file_name, file_size, subtitles_json, has_translated, updated_at) "
                "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
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