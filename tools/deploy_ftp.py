#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Выгрузка статического экспорта на хостинг по FTPS.

Секреты берутся только из окружения (в репозитории их нет):

    FTP_HOST      сервер, напр. ruvip69.hostiman.ru
    FTP_PORT      порт, по умолчанию 21
    FTP_USER      учётная запись FTP
    FTP_PASSWORD  пароль
    FTP_REMOTE_DIR удалённый каталог, напр. /kzvezdam.annakam.ru
    FTP_TLS       1 (по умолчанию) — явный FTPS с проверкой сертификата

Пример:
    python tools/deploy_ftp.py --src dist

Каталог выгрузки ограничен проверкой имени: по умолчанию разрешён только
/kzvezdam.annakam.ru, чтобы случайно не затронуть другие сайты аккаунта.
Файлы на сервере не удаляются: выгрузка только добавляет и заменяет.
"""
from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import ssl
import sys
import time
from ftplib import FTP_TLS, error_perm, error_temp
from pathlib import Path

EXPECTED_REMOTE = "/kzvezdam.annakam.ru"
ORDER = {  # сначала ресурсы, в конце — главная страница
    "static": 0,
    "read": 1,
    "chapters": 2,
    "promo": 3,
    "version.json": 4,
    "robots.txt": 5,
    ".htaccess": 6,
    "index.html": 9,
    "404.html": 10,
}


def sort_key(relative: str) -> tuple[int, str]:
    top = relative.split("/", 1)[0]
    return (ORDER.get(top, 5), relative)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Выгрузка статического сайта по FTPS")
    parser.add_argument("--src", default="dist", help="каталог с готовыми файлами")
    parser.add_argument("--remote-dir", default=os.environ.get("FTP_REMOTE_DIR", EXPECTED_REMOTE), help="удалённый каталог")
    parser.add_argument("--allow-any-dir", action="store_true", help="разрешить каталог, отличный от /kzvezdam.annakam.ru")
    parser.add_argument("--dry-run", action="store_true", help="только показать план")
    return parser.parse_args(argv)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def connect() -> FTP_TLS:
    host = env("FTP_HOST")
    port = int(env("FTP_PORT", "21"))
    user = env("FTP_USER")
    password = env("FTP_PASSWORD")
    if not (host and user and password):
        raise SystemExit("Не заданы FTP_HOST / FTP_USER / FTP_PASSWORD")
    if env("FTP_TLS", "1") in {"1", "true", "yes"}:
        ftp = FTP_TLS(context=ssl.create_default_context(), timeout=60)
        ftp.connect(host, port)
        ftp.login(user, password)
        ftp.prot_p()
        return ftp
    ftp = FTP_TLS(context=ssl._create_unverified_context(), timeout=60)
    ftp.connect(host, port)
    ftp.login(user, password)
    return ftp


def ensure_dir(ftp: FTP_TLS, remote: str) -> None:
    parts = [p for p in remote.strip("/").split("/") if p]
    ftp.cwd("/")
    for part in parts:
        try:
            ftp.cwd(part)
        except error_perm:
            ftp.mkd(part)
            ftp.cwd(part)


def upload(ftp: FTP_TLS, local: Path, remote: str) -> tuple[FTP_TLS, int]:
    """Выгружает файл и сверяет размер. При сбое переподключается и повторяет."""
    size = local.stat().st_size
    for attempt in range(1, 4):
        try:
            with local.open("rb") as stream:
                ftp.storbinary(f"STOR {remote}", stream, blocksize=1024 * 256)
            remote_size = ftp.size(remote)
            if remote_size != size:
                raise error_temp(f"размер на сервере {remote_size} != {size}")
            return ftp, size
        except (error_temp, error_perm, OSError, EOFError) as exc:
            if attempt == 3:
                raise SystemExit(f"{remote}: {type(exc).__name__}: {exc}")
            time.sleep(2 * attempt)
            try:
                ftp.close()
            except Exception:
                pass
            ftp = connect()
            ensure_dir(ftp, posixpath.dirname(remote))
    return ftp, size


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    src = Path(args.src).resolve()
    remote_dir = args.remote_dir.rstrip("/")
    if not remote_dir.startswith("/"):
        raise SystemExit("FTP_REMOTE_DIR должен быть абсолютным путём")
    if remote_dir != EXPECTED_REMOTE and not args.allow_any_dir:
        raise SystemExit(f"Каталог {remote_dir} не разрешён; ожидался {EXPECTED_REMOTE} (--allow-any-dir для исключения)")
    if not re.fullmatch(r"/[A-Za-z0-9._/-]+", remote_dir) or ".." in remote_dir.split("/"):
        raise SystemExit("Недопустимый путь выгрузки")
    if not (src / "index.html").is_file():
        raise SystemExit(f"В {src} нет index.html — это не собранный экспорт")

    files = sorted((p for p in src.rglob("*") if p.is_file()), key=lambda p: sort_key(p.relative_to(src).as_posix()))
    if args.dry_run:
        print(json.dumps({"would_upload": len(files), "remote": remote_dir,
                          "bytes": sum(p.stat().st_size for p in files)}, ensure_ascii=False))
        return 0

    ftp = connect()
    ensure_dir(ftp, remote_dir)
    print("remote:", ftp.pwd(), file=sys.stderr)

    total = 0
    uploaded = 0
    for path in files:
        relative = path.relative_to(src).as_posix()
        target = posixpath.join(remote_dir, relative)
        parent = posixpath.dirname(target)
        ensure_dir(ftp, parent)
        ftp, size = upload(ftp, path, target)
        total += size
        uploaded += 1

    ftp.quit()
    print(json.dumps({"remote": remote_dir, "uploaded": uploaded, "bytes": total}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
