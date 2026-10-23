#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка опубликованного сайта после выгрузки.

Проверяет HTTP-коды, canonical, отсутствие локальных адресов, отдачу видео
(video/mp4 + Range 206) и совпадение version.json с ожидаемым коммитом.

    python tools/verify_site.py --base https://kzvezdam.annakam.ru --expect-sha $GITHUB_SHA
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request


def fetch(base: str, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(base + path, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=45, context=ssl.create_default_context()) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверка опубликованного статического сайта")
    parser.add_argument("--base", default="https://kzvezdam.annakam.ru")
    parser.add_argument("--expect-sha", default="")
    parser.add_argument("--chapters", type=int, default=11)
    args = parser.parse_args(argv)
    base = args.base.rstrip("/")
    failures: list[str] = []

    def check(path: str, expect: int = 200, expect_noindex: bool = False) -> bytes:
        status, headers, body = fetch(base, path)
        if status != expect:
            failures.append(f"{path}: HTTP {status}, ожидался {expect}")
        if expect_noindex and not headers.get("X-Robots-Tag", "").startswith("noindex"):
            failures.append(f"{path}: нет X-Robots-Tag noindex")
        return body

    home = check("/", expect_noindex=True).decode("utf-8", "replace")
    if f'rel="canonical" href="{base}/"' not in home:
        failures.append("/: canonical не совпадает с адресом поддомена")
    if "127.0.0.1" in home or "localhost" in home:
        failures.append("/: в HTML остались локальные адреса")
    if "csrf-token" in home:
        failures.append("/: остался csrf-мета для несуществующего backend")

    check("/chapters", expect_noindex=True)
    for cid in range(1, args.chapters + 1):
        page = check(f"/read/{cid}", expect_noindex=True).decode("utf-8", "replace")
        if f'rel="canonical" href="{base}/read/{cid}"' not in page:
            failures.append(f"/read/{cid}: canonical")
        if "[video]" in page or "[img]" in page:
            failures.append(f"/read/{cid}: теги разметки видны как текст")

    prologue = fetch(base, "/read/1")[2].decode("utf-8", "replace")
    if '<video src="/static/video/prologue.mp4" controls playsinline preload="metadata"' not in prologue:
        failures.append("/read/1: нет плеера пролога с нужными атрибутами")
    if "autoplay" in prologue:
        failures.append("/read/1: у видео есть autoplay")

    status, headers, body = fetch(base, "/static/video/prologue.mp4", {"Range": "bytes=0-1023"})
    if status != 206:
        failures.append(f"видео: Range вернул {status}, ожидался 206")
    if not headers.get("Content-Range", "").startswith("bytes 0-1023/"):
        failures.append(f"видео: неверный Content-Range {headers.get('Content-Range')!r}")
    if headers.get("Content-Type") != "video/mp4":
        failures.append(f"видео: Content-Type {headers.get('Content-Type')!r}")
    if len(body) != 1024:
        failures.append(f"видео: в ответе {len(body)} байт вместо 1024")

    status, headers, _ = fetch(base, "/static/video/prologue.mp4", {"Range": "bytes=0-0"})
    if headers.get("Content-Type") != "video/mp4":
        failures.append("видео: HEAD-ответ без video/mp4")

    for asset in ("/static/css/style.css", "/static/js/hero.js", "/static/js/flyby.js",
                  "/static/chapter-images/pulkovo.jpg"):
        check(asset)

    check("/nonexistent-page", expect=404, expect_noindex=True)

    version = json.loads(check("/version.json").decode("utf-8"))
    if args.expect_sha and version.get("commit") and version["commit"] != args.expect_sha:
        failures.append(f"version.json: коммит {version['commit']} != ожидаемого {args.expect_sha}")
    if args.expect_sha and not version.get("commit"):
        failures.append("version.json: не записан коммит релиза")

    report = {"base": base, "version": version, "failures": failures}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
