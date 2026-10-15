"""One JSONL file. Every line is a lap with a check code."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def stamp_of(ask: str, did: str) -> str:
    raw = (ask or "") + "\n" + (did or "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def path_of(home: Path) -> Path:
    return Path(home) / "laps.jsonl"


def read_all(home: Path) -> list[dict]:
    file_path = path_of(home)
    if not file_path.is_file():
        return []
    rows = []
    for line in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def append(home: Path, event: dict) -> dict:
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    ask = str(event.get("ask") or "")[:2000]
    did = str(event.get("did") if event.get("did") is not None else "")[:8000]
    prior = read_all(home)
    votes = event.get("votes") or []
    clean_votes = []
    for vote in list(votes)[:12]:
        clean_votes.append(None if vote is None else str(vote)[:80])
    agree = event.get("agree")
    if agree is not None:
        agree = round(float(agree), 4)
    row = {
        "v": 1,
        "t": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lap": len(prior) + 1,
        "lane": str(event.get("lane") or "")[:20],
        "ask": ask,
        "did": did,
        "ms": round(float(event.get("ms") or 0), 2),
        "proof": str(event.get("proof") or "")[:20],
        "stamp": stamp_of(ask, did),
        "agree": agree,
        "votes": clean_votes,
    }
    with path_of(home).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def find_stamp(home: Path, code: str) -> dict | None:
    code = (code or "").strip().lower()
    for row in reversed(read_all(home)):
        if str(row.get("stamp") or "").lower() == code:
            return row
    return None
