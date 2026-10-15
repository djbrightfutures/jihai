"""ASCII cards. The file keeps the full answer. The card is the face."""

from __future__ import annotations

W = 62


def _show(text: str) -> str:
    out = []
    for ch in text or "":
        out.append(ch if 32 <= ord(ch) < 127 else "?")
    return "".join(out)


def _fit(text: str) -> str:
    inner = _show(text)
    if len(inner) > W:
        inner = inner[: W - 1] + ">"
    return "|" + inner.ljust(W) + "|"


def _rule() -> str:
    return "+" + ("-" * W) + "+"


def _pair(left: str, right: str) -> str:
    left = _show(left).strip()
    right = _show(right).strip()
    if right:
        gap = W - 2 - len(left) - len(right)
        if gap < 1:
            left = left[: max(0, W - 3 - len(right))]
            gap = 1
        inner = " " + left + (" " * gap) + right + " "
    else:
        inner = " " + left
    if len(inner) > W:
        inner = inner[: W - 1] + ">"
    return "|" + inner.ljust(W) + "|"


def _box(rows: list[str]) -> str:
    lines = [_rule()]
    for row in rows:
        lines.append(row if row[:1] == "|" else _fit(row))
    lines.append(_rule())
    return "\n".join(lines)


def banner() -> str:
    return _box([
        _fit(""),
        _fit(" JIHAI"),
        _fit(" november 4, 1995. scorpio."),
        _fit(" the pig on the year and the day."),
        _fit(" facts run here. a split vote escalates."),
        _fit(" the model's words are not rewritten."),
        _fit(""),
    ])


def _chunks(text: str, limit: int = 3) -> list[str]:
    """Wrap for the card. Newlines stay lines. The lap file keeps the rest."""
    source = text or ""
    parts = source.splitlines() or [""]
    lines: list[str] = []
    cut = False
    for part in parts:
        words = _show(part).split()
        if not words:
            if len(lines) < limit:
                lines.append(" ")
            else:
                cut = True
            continue
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if cur and len(" " + trial) > W:
                lines.append(" " + cur)
                cur = word
                if len(lines) >= limit:
                    cut = True
                    break
            else:
                cur = trial
        if cut:
            break
        if cur:
            if len(lines) >= limit:
                cut = True
                break
            lines.append(" " + cur)
    if not lines:
        return [" (empty)"]
    if cut and lines:
        lines[-1] = lines[-1][: W - 28].rstrip() + " ... full line is in the lap"
    return lines[:limit]


def card(row: dict) -> str:
    lap = int(row.get("lap") or 0)
    lane = str(row.get("lane") or "").upper()
    proof = str(row.get("proof") or "").upper()
    rows = [
        _pair("JIHAI", f"lap {lap:02d}"),
        _pair(lane, proof),
        _fit(""),
        _fit(f" {row.get('ms', 0)} ms"),
    ]
    if row.get("agree") is not None:
        rows.append(_fit(f" agree {float(row['agree']):.4f}"))
    rows.append(_fit(""))
    rows.append(_fit(" ASK"))
    rows.extend(_fit(line) for line in _chunks(str(row.get("ask") or "")))
    rows.append(_fit(" DID"))
    rows.extend(_fit(line) for line in _chunks(str(row.get("did") or ""), 6))
    votes = row.get("votes") or []
    if votes:
        shown = " ".join("." if vote is None else str(vote) for vote in votes)
        rows.append(_fit(" VOTES"))
        rows.append(_fit(" " + shown))
    rows.append(_fit(""))
    rows.append(_fit(f" STAMP  {row.get('stamp') or ''}"))
    return _box(rows)


def board(rows: list[dict], seats: str) -> str:
    body = [_pair("JIHAI", "BOARD"), _fit("")]
    if not rows:
        body.append(_fit(" no laps yet"))
    for row in rows[-8:]:
        ask = _show(str(row.get("ask") or "")).strip()
        room = W - 24
        if len(ask) > room:
            ask = ask[: room - 1] + ">"
        lane = str(row.get("lane") or "").upper()[:6]
        body.append(_fit(
            f" {int(row.get('lap') or 0):02d} {lane:<6} {row.get('ms', 0):>8} ms  {ask}"
        ))
    body.append(_fit(""))
    for line in (seats or "").splitlines():
        body.append(_fit(" " + line))
    return _box(body)
