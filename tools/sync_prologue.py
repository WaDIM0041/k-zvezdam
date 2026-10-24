"""Synchronize the canonical prologue manuscript into its static-site seed."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "content" / "prologue.txt"
SEED = ROOT / "chapters_seed.json"
PROVENANCE = ROOT / "CONTENT-PROVENANCE.json"


def main() -> None:
    body = MANUSCRIPT.read_text(encoding="utf-8").strip() + "\n"
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    prologue = next(item for item in seed if item["position"] == 0)
    prologue["body"] = body
    SEED.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    entry = next(item for item in provenance["chapters"] if item["position"] == 0)
    entry["bodySha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    PROVENANCE.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    database = ROOT / "instance" / "roman.db"
    if database.is_file():
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE chapters SET body = ? WHERE position = 0", (body,))


if __name__ == "__main__":
    main()
