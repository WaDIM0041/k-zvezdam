"""Sync the editable Chapter 1 manuscript into the seed and local reader database."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "content" / "chapter-01.txt"
SEED = ROOT / "chapters_seed.json"
DATABASE = ROOT / "instance" / "roman.db"
PROVENANCE = ROOT / "CONTENT-PROVENANCE.json"


def main() -> None:
    body = MANUSCRIPT.read_text(encoding="utf-8").strip() + "\n"
    rows = json.loads(SEED.read_text(encoding="utf-8"))
    chapter = next(item for item in rows if item["position"] == 1)
    chapter["body"] = body.rstrip("\n")
    chapter["chars"] = len(chapter["body"])
    SEED.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    record = next(item for item in provenance["chapters"] if item["position"] == 1)
    record["bodySource"] = "content/chapter-01.txt + static/chapter-01/"
    record["bodySha256"] = hashlib.sha256(chapter["body"].encode("utf-8")).hexdigest()
    record["revision"] = "Мультимедийная редакция по текущей публикации: видеоматериалы и иллюстрации привязаны к сценам."
    PROVENANCE.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with sqlite3.connect(DATABASE) as db:
        db.execute("UPDATE chapters SET body=?, updated_at=CURRENT_TIMESTAMP WHERE position=1", (chapter["body"],))
        db.commit()

    print(f"chapter 1 synced: {len(chapter['body'])} characters; sha256={record['bodySha256']}")


if __name__ == "__main__":
    main()
