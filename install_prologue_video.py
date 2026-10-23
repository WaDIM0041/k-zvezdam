"""Insert the prepared local video into the local prologue, preserving its text."""
import sqlite3
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parent
video = root / 'static/video/prologue.mp4'
database = root / 'instance/roman.db'
if not video.is_file() or not database.is_file():
    raise SystemExit('Prepared video or existing local database is missing')

tag = '[video]/static/video/prologue.mp4[/video]'
with sqlite3.connect(database) as db:
    matches = db.execute('SELECT id, body FROM chapters WHERE kind = ?', ('Пролог',)).fetchall()
    if len(matches) != 1:
        raise SystemExit('Expected exactly one prologue; database left unchanged')
    chapter_id, body = matches[0]
    if tag not in body:
        backup_path = database.with_name('before-video-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.backup')
        with sqlite3.connect(backup_path) as backup:
            db.backup(backup)
        db.execute('UPDATE chapters SET body = ? WHERE id = ?', (tag + '\n\n' + body, chapter_id))
        db.commit()
        print('Local prologue updated; backup:', backup_path)
    else:
        print('Video is already present; no changes')
    print(f'http://127.0.0.1:5002/read/{chapter_id}#readBody')
