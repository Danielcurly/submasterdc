import sqlite3
import json
import uuid
import os
import traceback

try:
    db_path = r'd:\Proyectos\Descargador Subtitulos\source\data\subtitle_manager.db'
    
    print("Connecting to DB...")
    conn = sqlite3.connect(db_path, timeout=10.0)
    
    # Ensure tables exist
    conn.execute('''
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS media_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT UNIQUE NOT NULL,
        file_name TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        subtitles_json TEXT NOT NULL,
        has_translated INTEGER DEFAULT 0,
        embedded_tracks_json TEXT DEFAULT '[]',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 1. Update Config
    print("Updating Config table...")
    cursor = conn.execute("SELECT value FROM config WHERE key = 'libraries'")
    row = cursor.fetchone()
    
    if row:
        libraries = json.loads(row[0])
    else:
        libraries = []
        
    has_lib = any(l.get('path') == '/data/demo_600' for l in libraries)
    if not has_lib:
        print("Adding Demo Library 600 to config table...")
        libraries.append({
            'id': str(uuid.uuid4())[:8],
            'name': 'Demo Library 600',
            'path': '/data/demo_600',
            'scan_mode': 'manual',
            'scan_interval_hours': 24
        })
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('libraries', ?)", (json.dumps(libraries),))
    else:
        print("Demo Library already in config table.")

    # 2. Update Media Files
    print("Inserting 600 rows into media_files...")
    # Use a faster batch insert
    conn.execute("DELETE FROM media_files WHERE file_path LIKE '/data/demo_600/%'")
    for i in range(600):
        conn.execute('''
            INSERT INTO media_files 
            (file_path, file_name, file_size, subtitles_json, has_translated, embedded_tracks_json, updated_at) 
            VALUES (?, ?, ?, ?, 0, ?, CURRENT_TIMESTAMP)
        ''', (f'/data/demo_600/video_{i}.mkv', f'video_{i}.mkv', 1024, '[]', '[]'))
    
    conn.commit()
    conn.close()
    print("Done! Demo library and 600 files are now in the DB.")
    
except Exception as e:
    print("ERROR:")
    traceback.print_exc()
