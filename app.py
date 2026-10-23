# -*- coding: utf-8 -*-
"""Flask preview reader for the selected local composite edition."""
from __future__ import annotations

import hmac
import html
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from flask import (
    Flask, abort, current_app, flash, g, jsonify, make_response, redirect,
    render_template, request, send_from_directory, session, url_for,
)
from markupsafe import Markup
from PIL import Image, UnidentifiedImageError

BASE = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = Path(os.environ.get("ROMAN_DATA_DIR") or str(BASE / "instance")).resolve()
Image.MAX_IMAGE_PIXELS = 30_000_000
ALLOWED_IMAGE_FORMATS = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "GIF": {".gif"},
    "WEBP": {".webp"},
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_BODY_CHARS = 1_500_000
BOOK_TITLE = "Через время к звёздам"
BOOK_AUTHOR = "ANNA Kamchatka"
BOOK_TAGLINE = ("Они прошли сквозь ад параллельных миров, чтобы вернуться домой. "
                "Но у Времени были другие планы.")
_LOGIN_FAILURES: dict[str, list[float]] = {}

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("ROMAN_SECRET") or secrets.token_urlsafe(48),
    DATA_DIR=str(DEFAULT_DATA_DIR),
    DB_PATH=os.environ.get("ROMAN_DB") or str(DEFAULT_DATA_DIR / "roman.db"),
    UPLOAD_DIR=os.environ.get("ROMAN_UPLOAD_DIR") or str(DEFAULT_DATA_DIR / "uploads"),
    CHAPTER_IMAGE_DIR=str(BASE / "static" / "chapter-images"),
    ADMIN_PASSWORD=os.environ.get("ROMAN_ADMIN_PASSWORD", ""),
    SITE_ORIGIN=(os.environ.get("SITE_ORIGIN") or "https://k-zvezdam.ru").rstrip("/"),
    PREVIEW_NOINDEX=os.environ.get("PREVIEW_NOINDEX", "1").lower() not in {"0", "false", "no"},
    STATIC_EXPORT=os.environ.get("ROMAN_STATIC_EXPORT", "0").lower() in {"1", "true", "yes"},
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"},
    PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
    MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES + 128 * 1024,
)


def db_path() -> Path:
    return Path(current_app.config["DB_PATH"]).resolve()


def ensure_data_dirs() -> None:
    Path(current_app.config["DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(current_app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)


def connect_db(path: Path | None = None) -> sqlite3.Connection:
    selected = path or db_path()
    selected.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(selected), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 10000")
    return db


def init_db(path: Path | None = None) -> None:
    ensure_data_dirs()
    db = connect_db(path)
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS chapters(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL DEFAULT 0,
                kind TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                slug TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                audio_url TEXT NOT NULL DEFAULT '',
                published INTEGER NOT NULL DEFAULT 1,
                views INTEGER NOT NULL DEFAULT 0,
                likes INTEGER NOT NULL DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cols = {r[1] for r in db.execute("PRAGMA table_info(chapters)")}
        additions = {
            "audio_url": "TEXT NOT NULL DEFAULT ''",
            "published": "INTEGER NOT NULL DEFAULT 1",
            "views": "INTEGER NOT NULL DEFAULT 0",
            "likes": "INTEGER NOT NULL DEFAULT 0",
            "slug": "TEXT NOT NULL DEFAULT ''",
            "kind": "TEXT NOT NULL DEFAULT ''",
            "created_at": "TEXT",
            "updated_at": "TEXT",
        }
        for name, declaration in additions.items():
            if name not in cols:
                db.execute(f"ALTER TABLE chapters ADD COLUMN {name} {declaration}")
        db.commit()
    finally:
        db.close()
    seed_if_empty(path)


def seed_if_empty(path: Path | None = None) -> None:
    selected = path or db_path()
    seed_file = BASE / "chapters_seed.json"
    db = connect_db(selected)
    try:
        if db.execute("SELECT COUNT(*) FROM chapters").fetchone()[0]:
            return
        records = json.loads(seed_file.read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc).isoformat()
        for chapter in records:
            title = str(chapter["title"]).strip()
            db.execute(
                "INSERT INTO chapters(position,kind,title,slug,body,audio_url,published,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (int(chapter["position"]), str(chapter.get("kind", ""))[:40], title,
                 slugify(title), str(chapter["body"]), "", 1, now, now),
            )
        db.commit()
    finally:
        db.close()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect_db()
    return g.db


@app.teardown_appcontext
def close_db(_exc: Exception | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def slugify(value: str) -> str:
    translit = str.maketrans({
        "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh","з":"z","и":"i","й":"y",
        "к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f",
        "х":"h","ц":"c","ч":"ch","ш":"sh","щ":"sch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
    })
    value = re.sub(r"[^a-z0-9]+", "-", str(value).lower().translate(translit)).strip("-")
    return value or "chapter"


def csrf_token() -> str:
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@app.before_request
def verify_csrf() -> None:
    g.csp_nonce = secrets.token_urlsafe(18)
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    supplied = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token", "")
    expected = session.get("_csrf_token", "")
    if not expected or not supplied or not hmac.compare_digest(str(expected).encode("utf-8"), str(supplied).encode("utf-8")):
        abort(400, description="Invalid CSRF token")


def _safe_next(value: str | None) -> str:
    if not value or "\\" in value or any(ord(ch) < 32 for ch in value):
        return url_for("admin")
    try:
        parsed = urlsplit(value)
        decoded_path = unquote(parsed.path or "")
    except ValueError:
        return url_for("admin")
    if (parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//")
            or decoded_path.startswith("//") or "\\" in decoded_path
            or any(part == ".." for part in decoded_path.split("/"))):
        return url_for("admin")
    return value


def admin_enabled() -> bool:
    return bool(str(current_app.config.get("ADMIN_PASSWORD", "")))


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not admin_enabled():
            abort(503, description="Админка отключена: пароль не настроен")
        if not session.get("admin"):
            return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped


def _valid_web_url(value: str, *, allow_root: bool = True) -> str | None:
    value = (value or "").strip()
    if not value or any(ord(c) < 32 for c in value) or "\\" in value:
        return None
    try:
        parsed = urlsplit(value)
        decoded_path = unquote(parsed.path or "")
    except ValueError:
        return None
    if parsed.scheme.lower() in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password:
        return value
    decoded = decoded_path
    if (allow_root and not parsed.scheme and not parsed.netloc and value.startswith("/")
            and not value.startswith("//") and not decoded.startswith("//")
            and all(part != ".." for part in decoded.split("/"))):
        return value
    return None


def _image_url(raw: str) -> str | None:
    value = _valid_web_url(raw)
    if not value:
        return None
    parsed = urlsplit(value)
    if not parsed.scheme and parsed.path.startswith("/static/uploads/"):
        name = parsed.path.rsplit("/", 1)[-1]
        if re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", name):
            return url_for("chapter_image", filename=name)
        return None
    return value


def _video_embed(raw_url: str) -> str:
    value = _valid_web_url(raw_url, allow_root=True)
    if not value:
        return "<p>Видео недоступно: ссылка не прошла проверку.</p>"
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}:
        video_id = ""
        if host.endswith("youtu.be"):
            video_id = parsed.path.strip("/").split("/")[0]
        elif parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            m = re.fullmatch(r"/(?:embed|shorts)/([A-Za-z0-9_-]{6,20})/?", parsed.path)
            video_id = m.group(1) if m else ""
        if re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id):
            return (f'<div class="embed"><iframe src="https://www.youtube-nocookie.com/embed/{video_id}" '
                    'title="YouTube video" loading="lazy" allowfullscreen></iframe></div>')
    if host in {"vk.com", "www.vk.com", "vkvideo.ru", "www.vkvideo.ru"}:
        m = re.fullmatch(r"/video(-?\d+)_(\d+)/?", parsed.path)
        if m:
            oid, vid = m.groups()
            return (f'<div class="embed"><iframe src="https://vk.com/video_ext.php?oid={oid}&amp;id={vid}" '
                    'title="VK video" loading="lazy" allowfullscreen></iframe></div>')
    if host in {"rutube.ru", "www.rutube.ru"}:
        m = re.fullmatch(r"/video/([A-Za-z0-9]+)/?", parsed.path)
        if m:
            return (f'<div class="embed"><iframe src="https://rutube.ru/play/embed/{m.group(1)}" '
                    'title="Rutube video" loading="lazy" allowfullscreen></iframe></div>')
    if parsed.path.lower().endswith((".mp4", ".webm", ".ogg")):
        safe_url = html.escape(value, quote=True)
        return (f'<div class="embed"><video src="{safe_url}" controls playsinline preload="metadata" '
                f'aria-label="Видео к главе">Ваш браузер не поддерживает видео. '
                f'<a href="{safe_url}">Открыть видео</a></video></div>'
                f'<p class="video-fallback"><a href="{safe_url}" target="_blank" '
                'rel="noopener noreferrer">Открыть видео отдельно ↗</a></p>')
    return f'<p><a href="{html.escape(value, quote=True)}" target="_blank" rel="noopener noreferrer">Видео ↗</a></p>'


def _inline(value: str) -> str:
    escaped = html.escape(value, quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", escaped)


def render_body(body: str) -> Markup:
    chunks = re.split(r"\n\s*\n", (body or "").replace("\r\n", "\n").strip())
    rendered: list[str] = []
    for chunk in chunks:
        text = chunk.strip()
        if not text:
            continue
        image = re.fullmatch(r"\[img\](.+?)\[/img\]", text, re.S)
        if image:
            src = _image_url(image.group(1))
            if src:
                rendered.append(f'<figure class="c-img"><img src="{html.escape(src, quote=True)}" alt="" loading="lazy"></figure>')
            continue
        video = re.fullmatch(r"\[video\](.+?)\[/video\]", text, re.S)
        if video:
            rendered.append(_video_embed(video.group(1)))
            continue
        audio = re.fullmatch(r"\[audio\](.+?)\[/audio\]", text, re.S)
        if audio:
            src = _valid_web_url(audio.group(1), allow_root=False)
            if src:
                rendered.append(f'<div class="c-audio"><audio src="{html.escape(src, quote=True)}" controls preload="none"></audio></div>')
            continue
        para = "<br>".join(_inline(line) for line in text.split("\n"))
        rendered.append(f"<p>{para}</p>")
    return Markup("\n".join(rendered))


def excerpt(body: str, n: int = 160) -> str:
    clean = re.sub(r"\[(?:img|video|audio)\].*?\[/(?:img|video|audio)\]", " ", body or "", flags=re.S)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:n] + ("…" if len(clean) > n else "")


def reading_time(body: str) -> int:
    clean = re.sub(r"\[(?:img|video|audio)\].*?\[/(?:img|video|audio)\]", " ", body or "", flags=re.S)
    return max(1, round(len(re.findall(r"\S+", clean)) / 170))


@app.context_processor
def template_globals():
    canonical = current_app.config["SITE_ORIGIN"] + request.path
    return {
        "BOOK_TITLE": BOOK_TITLE, "BOOK_AUTHOR": BOOK_AUTHOR, "BOOK_TAGLINE": BOOK_TAGLINE,
        "is_admin": bool(session.get("admin")), "year": datetime.now().year,
        "excerpt": excerpt, "reading_time": reading_time, "csrf_token": csrf_token,
        "canonical_url": canonical, "csp_nonce": getattr(g, "csp_nonce", ""),
        "static_export": bool(current_app.config.get("STATIC_EXPORT")),
    }


def _latest_login_times(key: str) -> list[float]:
    now = time.monotonic()
    recent = [t for t in _LOGIN_FAILURES.get(key, []) if now - t < 900]
    _LOGIN_FAILURES[key] = recent
    return recent


@app.route("/")
def index():
    rows = get_db().execute("SELECT * FROM chapters WHERE published=1 ORDER BY position, id").fetchall()
    return render_template("index.html", chapters=rows)


@app.route("/chapters")
def chapters():
    rows = get_db().execute("SELECT * FROM chapters WHERE published=1 ORDER BY position, id").fetchall()
    return render_template("chapters.html", chapters=rows)


@app.route("/read/<int:cid>")
def read(cid: int):
    db = get_db()
    chapter = db.execute("SELECT * FROM chapters WHERE id=? AND published=1", (cid,)).fetchone()
    if chapter is None:
        abort(404)
    if not session.get("admin"):
        db.execute("UPDATE chapters SET views=views+1 WHERE id=?", (cid,))
        db.commit()
        chapter = db.execute("SELECT * FROM chapters WHERE id=?", (cid,)).fetchone()
    all_chapters = db.execute(
        "SELECT id,kind,title,position FROM chapters WHERE published=1 ORDER BY position,id"
    ).fetchall()
    idx = next((i for i, row in enumerate(all_chapters) if row["id"] == cid), 0)
    return render_template(
        "read.html", ch=chapter, body=render_body(chapter["body"]),
        prev_ch=all_chapters[idx-1] if idx else None,
        next_ch=all_chapters[idx+1] if idx+1 < len(all_chapters) else None,
        all_chapters=all_chapters,
    )


@app.route("/like/<int:cid>", methods=["POST"])
def like(cid: int):
    db = get_db()
    exists = db.execute("SELECT 1 FROM chapters WHERE id=? AND published=1", (cid,)).fetchone()
    if not exists:
        abort(404)
    db.execute("UPDATE chapters SET likes=likes+1 WHERE id=?", (cid,))
    db.commit()
    count = db.execute("SELECT likes FROM chapters WHERE id=?", (cid,)).fetchone()["likes"]
    return jsonify(likes=count)


@app.route("/promo")
def promo():
    promo_path = BASE / "promo" / "landing.html"
    markup = promo_path.read_text(encoding="utf-8")
    canonical = html.escape(current_app.config["SITE_ORIGIN"] + request.path, quote=True)
    marker = "<head>"
    additions = ("<meta name=\"robots\" content=\"noindex,nofollow,noarchive\">"
                 f"<link rel=\"canonical\" href=\"{canonical}\">")
    if marker in markup:
        markup = markup.replace(marker, marker + additions, 1)
    markup = markup.replace("__CSP_NONCE__", getattr(g, "csp_nonce", ""))
    return current_app.response_class(markup, mimetype="text/html")


@app.route("/media/<path:filename>")
def media_upload(filename: str):
    if Path(filename).name != filename or not re.fullmatch(r"[A-Za-z0-9_-]{16,80}\.(?:jpe?g|png|gif|webp)", filename, re.I):
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_DIR"], filename, conditional=True, max_age=3600)


@app.route("/chapter-images/<path:filename>")
def chapter_image(filename: str):
    if Path(filename).name != filename or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}\.(?:jpe?g|png|gif|webp)", filename, re.I):
        abort(404)
    return send_from_directory(current_app.config["CHAPTER_IMAGE_DIR"], filename, conditional=True, max_age=86400)


@app.route("/robots.txt")
def robots():
    return current_app.response_class("User-agent: *\nDisallow: /\n", mimetype="text/plain")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if not admin_enabled():
        abort(503, description="Админка отключена: задайте ROMAN_ADMIN_PASSWORD")
    if request.method == "POST":
        key = request.remote_addr or "local"
        attempts = _latest_login_times(key)
        if len(attempts) >= 5:
            abort(429, description="Слишком много попыток входа")
        expected = str(current_app.config["ADMIN_PASSWORD"])
        supplied = request.form.get("password", "")
        if hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
            _LOGIN_FAILURES.pop(key, None)
            session.clear()
            session["admin"] = True
            session.permanent = True
            target = _safe_next(request.form.get("next") or request.args.get("next"))
            return redirect(target)
        attempts.append(time.monotonic())
        flash("Неверный пароль", "err")
        return render_template("admin_login.html", next_url=_safe_next(request.form.get("next") or request.args.get("next"))), 401
    return render_template("admin_login.html", next_url=_safe_next(request.args.get("next")))


@app.route("/admin/logout", methods=["POST"])
@login_required
def admin_logout():
    session.clear()
    flash("Вы вышли из админки", "ok")
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
def admin():
    rows = get_db().execute("SELECT * FROM chapters ORDER BY position,id").fetchall()
    return render_template("admin.html", chapters=rows)


@app.route("/admin/new", methods=["GET", "POST"])
@login_required
def admin_new():
    db = get_db()
    if request.method == "POST":
        if not _save(db, None):
            return render_template("admin_edit.html", ch=None, nextpos=_next_position(db)), 400
        flash("Глава сохранена", "ok")
        return redirect(url_for("admin"))
    return render_template("admin_edit.html", ch=None, nextpos=_next_position(db))


def _next_position(db: sqlite3.Connection) -> int:
    row = db.execute("SELECT COALESCE(MAX(position),-1)+1 AS n FROM chapters").fetchone()
    return int(row["n"])


@app.route("/admin/edit/<int:cid>", methods=["GET", "POST"])
@login_required
def admin_edit(cid: int):
    db = get_db()
    chapter = db.execute("SELECT * FROM chapters WHERE id=?", (cid,)).fetchone()
    if chapter is None:
        abort(404)
    if request.method == "POST":
        if not _save(db, cid):
            return render_template("admin_edit.html", ch=chapter, nextpos=chapter["position"]), 400
        flash("Изменения сохранены", "ok")
        return redirect(url_for("admin"))
    return render_template("admin_edit.html", ch=chapter, nextpos=chapter["position"])


def _save(db: sqlite3.Connection, cid: int | None) -> bool:
    form = request.form
    title = form.get("title", "").strip()
    kind = form.get("kind", "").strip()
    body = form.get("body", "").replace("\r\n", "\n").strip()
    audio = form.get("audio_url", "").strip()
    try:
        position = int(form.get("position", "0"))
    except ValueError:
        flash("Позиция должна быть целым числом", "err")
        return False
    if not title or len(title) > 180 or len(kind) > 40 or len(body) > MAX_BODY_CHARS or not 0 <= position <= 100_000:
        flash("Проверьте название, тип, текст и позицию главы", "err")
        return False
    if audio and not _valid_web_url(audio, allow_root=False):
        flash("Для аудио нужна безопасная ссылка http или https", "err")
        return False
    published = 1 if form.get("published") == "on" else 0
    now = datetime.now(timezone.utc).isoformat()
    if cid is None:
        db.execute(
            "INSERT INTO chapters(position,kind,title,slug,body,audio_url,published,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (position, kind, title, slugify(title), body, audio, published, now, now),
        )
    else:
        db.execute(
            "UPDATE chapters SET position=?,kind=?,title=?,slug=?,body=?,audio_url=?,published=?,updated_at=? WHERE id=?",
            (position, kind, title, slugify(title), body, audio, published, now, cid),
        )
    db.commit()
    return True


@app.route("/admin/delete/<int:cid>", methods=["POST"])
@login_required
def admin_delete(cid: int):
    db = get_db()
    if db.execute("SELECT 1 FROM chapters WHERE id=?", (cid,)).fetchone() is None:
        abort(404)
    db.execute("DELETE FROM chapters WHERE id=?", (cid,))
    db.commit()
    flash("Глава удалена", "ok")
    return redirect(url_for("admin"))


@app.route("/admin/move/<int:cid>/<direction>", methods=["POST"])
@login_required
def admin_move(cid: int, direction: str):
    if direction not in {"up", "down"}:
        abort(404)
    db = get_db()
    rows = db.execute("SELECT id,position FROM chapters ORDER BY position,id").fetchall()
    idx = next((i for i, row in enumerate(rows) if row["id"] == cid), None)
    if idx is None:
        abort(404)
    other_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= other_idx < len(rows):
        current, other = rows[idx], rows[other_idx]
        db.execute("UPDATE chapters SET position=? WHERE id=?", (other["position"], current["id"]))
        db.execute("UPDATE chapters SET position=? WHERE id=?", (current["position"], other["id"]))
        db.commit()
    return redirect(url_for("admin"))


@app.route("/admin/toggle/<int:cid>", methods=["POST"])
@login_required
def admin_toggle(cid: int):
    db = get_db()
    chapter = db.execute("SELECT published FROM chapters WHERE id=?", (cid,)).fetchone()
    if chapter is None:
        abort(404)
    db.execute("UPDATE chapters SET published=? WHERE id=?", (0 if chapter["published"] else 1, cid))
    db.commit()
    return redirect(url_for("admin"))


@app.route("/admin/upload", methods=["POST"])
@login_required
def admin_upload():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify(error="Файл не выбран"), 400
    suffix = Path(uploaded.filename).suffix.lower()
    try:
        uploaded.stream.seek(0, os.SEEK_END)
        size = uploaded.stream.tell()
        uploaded.stream.seek(0)
    except (OSError, AttributeError):
        return jsonify(error="Не удалось прочитать файл"), 400
    if size <= 0 or size > MAX_UPLOAD_BYTES:
        return jsonify(error="Изображение превышает лимит 5 MiB или пустое"), 400
    try:
        with Image.open(uploaded.stream) as image:
            fmt = image.format
            width, height = image.size
            if fmt not in ALLOWED_IMAGE_FORMATS or suffix not in ALLOWED_IMAGE_FORMATS[fmt]:
                return jsonify(error="Тип файла не совпадает с форматом изображения"), 400
            if width < 1 or height < 1 or width * height > Image.MAX_IMAGE_PIXELS:
                return jsonify(error="Недопустимый размер изображения"), 400
            image.verify()
        uploaded.stream.seek(0)
        with Image.open(uploaded.stream) as image:
            image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return jsonify(error="Файл не является корректным изображением"), 400
    name = secrets.token_hex(16) + suffix
    destination = Path(current_app.config["UPLOAD_DIR"]).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / name
    uploaded.stream.seek(0)
    target.write_bytes(uploaded.stream.read(MAX_UPLOAD_BYTES + 1))
    return jsonify(url=url_for("media_upload", filename=name)), 201


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error="Запрос превышает допустимый размер"), 413


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    nonce = getattr(g, "csp_nonce", "")
    response.headers["Content-Security-Policy-Report-Only"] = (
        "default-src \'self\'; base-uri \'self\'; object-src \'none\'; frame-ancestors \'none\'; "
        f"script-src \'self\' \'nonce-{nonce}\' https://cdnjs.cloudflare.com; "
        f"style-src \'self\' \'nonce-{nonce}\' https://fonts.googleapis.com; "
        "style-src-attr \'unsafe-inline\'; img-src \'self\' https: data:; "
        "font-src \'self\' https://fonts.gstatic.com; connect-src \'self\'; "
        "media-src \'self\' https:; frame-src https://www.youtube-nocookie.com https://youtube.com https://vk.com https://rutube.ru; form-action \'self\'"
    )
    if current_app.config.get("PREVIEW_NOINDEX", True):
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
