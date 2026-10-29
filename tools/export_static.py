#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Статический экспорт читалки «Через время к звёздам» для kzvezdam.annakam.ru.

Flask-приложение на виртуальном хостинге не запускается (нет WSGI/SSH), поэтому
готовые страницы рендерятся здесь и выгружаются как обычные файлы:

    /                     -> index.html
    /chapters             -> chapters/index.html
    /read/<id>            -> read/<id>/index.html
    /promo                -> promo/index.html
    /static/**            -> static/**  (копируется как есть)

Экспорт работает на копии базы: рабочая instance/roman.db не изменяется,
счётчики просмотров не «накручиваются». Если базы нет (например, в CI), она
создаётся из chapters_seed.json, а в пролог добавляется блок [video].

Пример:
    python tools/export_static.py --out dist
    python tools/export_static.py --out dist --origin https://kzvezdam.annakam.ru
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ORIGIN = "https://kzvezdam.annakam.ru"
DEFAULT_VIDEO_TAG = "[video]/static/video/prologue.mp4[/video]"
MARKER = ".static-export"

HTACCESS = """# kzvezdam.annakam.ru — статический экспорт читалки.
# Flask на виртуальном хостинге не используется: отдаются готовые файлы.

Options -Indexes
DirectoryIndex index.html
ErrorDocument 404 /404.html

AddType video/mp4 .mp4
AddType video/webm .webm
AddType image/svg+xml .svg
AddType application/json .json

<IfModule mod_rewrite.c>
  RewriteEngine On
  # Красивые адреса без слеша на конце: /read/1, /chapters, /promo
  RewriteRule ^read/([0-9]+)/?$ read/$1/index.html [L]
  RewriteRule ^read/?$ chapters/index.html [L]
  RewriteRule ^chapters/?$ chapters/index.html [L]
  RewriteRule ^promo/?$ promo/index.html [L]
</IfModule>

<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/plain text/css application/javascript application/json image/svg+xml
</IfModule>

<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresByType text/html "access plus 0 seconds"
  ExpiresByType text/css "access plus 7 days"
  ExpiresByType application/javascript "access plus 7 days"
  ExpiresByType application/json "access plus 0 seconds"
  ExpiresByType image/jpeg "access plus 30 days"
  ExpiresByType image/png "access plus 30 days"
  ExpiresByType image/webp "access plus 30 days"
  ExpiresByType image/svg+xml "access plus 7 days"
  ExpiresByType video/mp4 "access plus 30 days"
</IfModule>

<IfModule mod_headers.c>
  Header always set X-Content-Type-Options "nosniff"
  Header always set X-Frame-Options "DENY"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
  # Preview-поддомен закрыт от индексации; индексация k-zvezdam.ru не затрагивается.
  Header always set X-Robots-Tag "noindex, nofollow, noarchive"
</IfModule>

# Служебные и серверные файлы в этом каталоге не нужны и не должны исполняться.
<IfModule mod_authz_core.c>
  <FilesMatch "^\\.(?!well-known)">
    Require all denied
  </FilesMatch>
  <FilesMatch "\\.(php|phtml|phar|cgi|pl|py|sh)$">
    Require all denied
  </FilesMatch>
</IfModule>
"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Статический экспорт читалки «К звёздам»")
    parser.add_argument("--out", default="dist", help="каталог результата (по умолчанию dist)")
    parser.add_argument("--origin", default=DEFAULT_ORIGIN, help="canonical-origin сайта")
    parser.add_argument("--db", default=None, help="исходная SQLite-база (копируется, не меняется)")
    parser.add_argument("--no-video", action="store_true", help="не добавлять блок [video] в пролог")
    parser.add_argument("--base-path", default="", help="префикс адресов для GitHub Pages")
    return parser.parse_args(argv)


def prepare_out(out: Path) -> None:
    if out.exists():
        contents = list(out.iterdir())
        if contents and not (out / MARKER).exists():
            raise SystemExit(f"Каталог {out} не пуст и не является прошлым экспортом — остановлено.")
        shutil.rmtree(out)
    out.mkdir(parents=True)


def prepare_db(source: Path | None, workdir: Path) -> Path:
    target = workdir / "export.db"
    if source is None:
        return target  # база будет создана и засеяна приложением
    if not source.is_file():
        raise SystemExit(f"Не найдена база: {source}")
    shutil.copy2(source, target)
    return target


def ensure_prologue_video(db_path: Path, tag: str) -> int | None:
    """Вставляет блок [video] первым абзацем пролога. Идемпотентно."""
    if not db_path.is_file():
        raise SystemExit("База экспорта не создана")
    with sqlite3.connect(str(db_path)) as db:
        rows = db.execute("SELECT id, body FROM chapters WHERE kind = ?", ("Пролог",)).fetchall()
        if len(rows) != 1:
            raise SystemExit(f"Ожидался ровно один пролог, найдено: {len(rows)}")
        chapter_id, body = rows[0]
        if tag not in body:
            db.execute("UPDATE chapters SET body = ? WHERE id = ?", (tag + "\n\n" + body, chapter_id))
            db.commit()
        return int(chapter_id)


def postprocess(html: str) -> str:
    """Правки HTML после рендера Flask-шаблона."""
    html = re.sub(r'[ \t]*<meta name="csrf-token"[^>]*>\n?', "", html)
    # Картинки глав лежат в static/chapter-images — избавляемся от отдельного маршрута Flask.
    html = html.replace('"/chapter-images/', '"/static/chapter-images/')
    return html


def check_no_local_refs(html: str, where: str) -> None:
    for needle in ("127.0.0.1", "localhost", ":5001", ":5002"):
        if needle in html:
            raise SystemExit(f"{where}: найден локальный адрес {needle}")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out = Path(args.out).resolve()
    origin = args.origin.rstrip("/")
    source_db = Path(args.db).resolve() if args.db else None

    prepare_out(out)

    saved_env = dict(os.environ)
    workdir = Path(tempfile.mkdtemp(prefix="kzvezdam-export-"))
    try:
        db_path = prepare_db(source_db, workdir)
        os.environ["ROMAN_DB"] = str(db_path)
        os.environ["ROMAN_DATA_DIR"] = str(workdir / "data")
        os.environ["ROMAN_UPLOAD_DIR"] = str(workdir / "uploads")
        os.environ["SITE_ORIGIN"] = origin
        os.environ["PREVIEW_NOINDEX"] = "1"
        os.environ["ROMAN_STATIC_EXPORT"] = "1"
        os.environ["ROMAN_ADMIN_PASSWORD"] = ""

        sys.path.insert(0, str(ROOT))
        import app as site  # noqa: E402  (импорт после подготовки окружения)

        site.app.config.update(
            TESTING=True,
            SITE_ORIGIN=origin,
            PREVIEW_NOINDEX=True,
            STATIC_EXPORT=True,
            ADMIN_PASSWORD="",
            DB_PATH=str(db_path),
        )
        with site.app.app_context():
            site.init_db(db_path)

        # The curated edition carries its own media placement, including the opening.
        with sqlite3.connect(str(db_path)) as db:
            curated = db.execute("SELECT body FROM chapters WHERE kind='Пролог'").fetchone()
        if not args.no_video and not (curated and "[scene]opening[/scene]" in curated[0]):
            ensure_prologue_video(db_path, DEFAULT_VIDEO_TAG)

        client = site.app.test_client()
        with site.app.app_context():
            db = site.connect_db(db_path)
            try:
                chapters = db.execute(
                    "SELECT id FROM chapters WHERE published=1 ORDER BY position, id"
                ).fetchall()
            finally:
                db.close()
        if not chapters:
            raise SystemExit("В базе нет опубликованных глав")

        written: list[str] = []

        def fetch(path: str) -> str:
            response = client.get(path)
            if response.status_code != 200:
                raise SystemExit(f"{path}: HTTP {response.status_code}")
            html = postprocess(response.get_data(as_text=True))
            prefix = args.base_path.rstrip("/")
            if prefix:
                if not re.fullmatch(r"/[A-Za-z0-9_-]+", prefix):
                    raise SystemExit("Недопустимый base-path")
                html = re.sub(r'((?:href|src|poster)=")/(?!/)', lambda m: m[1] + prefix + "/", html)
            check_no_local_refs(html, path)
            return html

        write(out / "index.html", fetch("/"))
        written.append("/")

        write(out / "chapters" / "index.html", fetch("/chapters"))
        written.append("/chapters")

        for row in chapters:
            cid = int(row["id"])
            write(out / "read" / str(cid) / "index.html", fetch(f"/read/{cid}"))
            written.append(f"/read/{cid}")

        write(out / "promo" / "index.html", fetch("/promo"))
        written.append("/promo")

        robots = client.get("/robots.txt").get_data(as_text=True)
        write(out / "robots.txt", robots)

        with site.app.test_request_context("/404"):
            not_found = postprocess(site.render_template("404.html"))
        if args.base_path:
            not_found = re.sub(r'((?:href|src|poster)=")/(?!/)', lambda m: m[1] + args.base_path.rstrip("/") + "/", not_found)
        check_no_local_refs(not_found, "404")
        write(out / "404.html", not_found)
        written.append("/404.html")

        shutil.copytree(ROOT / "static", out / "static")

        # The chapter-2 edition is a self-contained reader with its checked media.
        chapter_two = ROOT / "editions" / "chapter-02-v003"
        if (chapter_two / "index.html").is_file():
            shutil.copytree(chapter_two, out / "read" / "3", dirs_exist_ok=True)
            chapter_version = {
                "edition": "chapter-02-v003",
                "commit": os.environ.get("GITHUB_SHA", ""),
                "source": "editions/chapter-02-v003",
                "builtAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            write(out / "read" / "3" / "version.json",
                  json.dumps(chapter_version, ensure_ascii=False, indent=2) + "\n")
        write(out / ".htaccess", HTACCESS)
        write(out / MARKER, "static export of the Flask reader\n")
        write(out / ".nojekyll", "")

        version = {
            "site": origin,
            "builtAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "commit": os.environ.get("GITHUB_SHA", "") or "",
            "chapters": len(chapters),
            "pages": written,
            "noindex": True,
        }
        write(out / "version.json", json.dumps(version, ensure_ascii=False, indent=2) + "\n")

        files = [p for p in out.rglob("*") if p.is_file()]
        total = sum(p.stat().st_size for p in files)
        print(json.dumps({
            "out": str(out),
            "pages": len(written),
            "chapters": len(chapters),
            "files": len(files),
            "bytes": total,
            "origin": origin,
        }, ensure_ascii=False))
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        os.environ.clear()
        os.environ.update(saved_env)


if __name__ == "__main__":
    raise SystemExit(main())
