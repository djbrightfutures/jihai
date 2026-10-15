"""The desk. Facts never wait on GLM. A split vote does."""

from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__
from .card import banner, board, card
from .hands import PURE, hands
from .judge import collect, parse_choose, unanimous
from .laps import append, find_stamp, read_all, stamp_of
from .seat import live_glm, make_fast_once, seats_text

_FAST = object()


def home_dir() -> Path:
    raw = (os.environ.get("KEEN_HOME") or "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".keen"


def _messages(home: Path, ask: str) -> list[dict]:
    """Prior laps are context. The current ask is the last user line, unchanged."""
    out = []
    for row in read_all(home)[-4:]:
        out.append({"role": "user", "content": str(row.get("ask") or "")[:500]})
        out.append({"role": "assistant", "content": str(row.get("did") or "")[:500]})
    out.append({"role": "user", "content": ask})
    return out


def answer(ask: str, home: Path | None = None, *, glm_fn=None, fast_once=_FAST, k: int = 3) -> dict:
    """One lap. glm_fn(messages) -> text. fast_once(text, options) -> raw vote."""
    home = Path(home) if home is not None else home_dir()
    if glm_fn is None:
        glm_fn = live_glm
    if fast_once is _FAST:
        fast_once = make_fast_once()
    text = (ask or "").strip()
    started = time.perf_counter()
    votes: list = []
    agree = None
    choice = parse_choose(text)
    fact = None if choice else hands(text)
    if fact is not None:
        did, lane, proof = fact, "hands", "machine"
    elif choice and fast_once is not None:
        options, body = choice
        label, share, votes = collect(body, options, fast_once, k=k)
        agree = share
        if unanimous(label, share):
            did, lane, proof = label, "judge", "unanimous"
        else:
            did, lane, proof = glm_fn(_messages(home, text)), "glm", "escalate"
    elif choice:
        did, lane, proof = glm_fn(_messages(home, text)), "glm", "escalate"
    else:
        did, lane, proof = glm_fn(_messages(home, text)), "glm", "model"
    ms = (time.perf_counter() - started) * 1000
    row = append(home, {
        "lane": lane,
        "ask": text,
        "did": did,
        "ms": ms,
        "proof": proof,
        "agree": agree,
        "votes": votes,
    })
    _write_face(home, card(row))
    return row


def _write_face(home: Path, text: str) -> None:
    Path(home).mkdir(parents=True, exist_ok=True)
    (Path(home) / "keen.txt").write_text(text + "\n", encoding="utf-8")


def prove(home: Path) -> dict:
    """Re-run pure facts. Leave runs, reads, and model laps alone."""
    started = time.perf_counter()
    witnessed = drifted = tampered = left = 0
    rows = read_all(home)[-500:]
    for row in rows:
        if row.get("lane") != "hands":
            left += 1
            continue
        ask = str(row.get("ask") or "")
        cmd = ask.split(" ", 1)[0].lower() if ask else ""
        if cmd not in PURE or ask.strip() != cmd:
            left += 1
            continue
        did = str(row.get("did") or "")
        if row.get("stamp") and row.get("stamp") != stamp_of(ask, did):
            tampered += 1
            continue
        if hands(ask) == did:
            witnessed += 1
        else:
            drifted += 1
    summary = (
        f"facts checked {witnessed + drifted + tampered}\n"
        f"witnessed {witnessed}\n"
        f"drifted {drifted}\n"
        f"tampered {tampered}\n"
        f"left alone {left}\n"
        "model laps are not re-run. a model is not a fact."
    )
    ms = (time.perf_counter() - started) * 1000
    checked = witnessed + drifted + tampered
    if checked == 0:
        proof = "empty"
    elif tampered == 0 and drifted == 0:
        proof = "witnessed"
    else:
        proof = "drifted"
    row = append(home, {
        "lane": "prove",
        "ask": "prove",
        "did": summary,
        "ms": ms,
        "proof": proof,
        "agree": None,
        "votes": [],
    })
    _write_face(home, card(row))
    return row


def bench(n: int = 40, hop=None) -> tuple[float, float | None]:
    """Mean milliseconds. Hands stay in process. hop is one local HTTP call."""
    started = time.perf_counter()
    for _ in range(n):
        hands("hostname")
    hands_ms = (time.perf_counter() - started) * 1000 / n
    if hop is None:
        return hands_ms, None
    started = time.perf_counter()
    for _ in range(n):
        hop()
    hop_ms = (time.perf_counter() - started) * 1000 / n
    return hands_ms, hop_ms


class _Hop(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        body = b'{"choices":[{"message":{"content":"hop"}}]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def hop_server():
    """A local server that returns the word hop. Caller must shutdown()."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Hop)
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def measured_hop(n: int = 40) -> tuple[float, float]:
    """Hands against a loopback chat completion. No model is loaded."""
    import urllib.request
    server = hop_server()
    host, port = server.server_address
    url = f"http://{host}:{port}/v1/chat/completions"

    def hop():
        req = urllib.request.Request(
            url,
            data=b'{"model":"hop","messages":[{"role":"user","content":"hostname"}]}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()

    try:
        hands_ms, hop_ms = bench(n, hop)
    finally:
        server.shutdown()
        server.server_close()
    return hands_ms, hop_ms or 0.0


def face(home: Path) -> str:
    rows = read_all(home)
    parts = [banner(), ""]
    if rows:
        parts.append(card(rows[-1]))
        parts.append("")
    parts.append(board(rows, seats_text()))
    return "\n".join(parts)


def help_text() -> str:
    return (
        f"Keen {__version__}. The open GLM desk.\n"
        "\n"
        "  python -m keen hostname\n"
        "  python -m keen choose yes|no :: ship it\n"
        "  python -m keen pit\n"
        "  python -m keen prove\n"
        "  python -m keen bench\n"
        "  python -m keen stamp <code>\n"
        "  python -m keen seats\n"
        "  python -m keen tail\n"
        "\n"
        "A fact runs in this process. A choose line takes 3 votes on the fast\n"
        "seat. Unanimous keeps the label. Anything else goes to GLM.\n"
        "GLM's words are stored as they arrived.\n"
        "The lap file is ~/.keen/laps.jsonl\n"
        "KEEN_GLM_URL  KEEN_GLM_KEY  KEEN_GLM_MODEL  KEEN_FAST_URL\n"
        "A key can also live in ZHIPU_API_KEY. It is never written down."
    )


def perform(argv: list[str], home: Path | None = None) -> tuple[int, str]:
    home = Path(home) if home is not None else home_dir()
    args = list(argv or [])
    if not args or args[0] in ("-h", "--help", "help"):
        return 0, help_text()
    cmd = args[0].lower()
    if cmd == "version":
        return 0, __version__
    if cmd == "seats":
        return 0, seats_text()
    if cmd == "pit":
        return 0, face(home)
    if cmd == "tail":
        rows = read_all(home)[-8:]
        if not rows:
            return 0, "no laps yet"
        return 0, "\n".join(card(row) for row in rows)
    if cmd == "stamp" and len(args) > 1:
        row = find_stamp(home, args[1])
        if not row:
            return 2, "no lap with that stamp"
        return 0, card(row)
    if cmd == "prove":
        return 0, card(prove(home))
    if cmd == "bench":
        n = 40
        if len(args) > 1 and args[1].isdigit():
            n = max(1, min(200, int(args[1])))
        hands_ms, hop_ms = measured_hop(n)
        faster = hands_ms < hop_ms
        return 0, (
            f"n {n}\n"
            f"hands {hands_ms:.2f} ms\n"
            f"hop {hop_ms:.2f} ms\n"
            f"faster {faster}"
        )
    if cmd == "ask":
        text = " ".join(args[1:]).strip()
    else:
        text = " ".join(args).strip()
    if not text:
        return 0, help_text()
    return 0, card(answer(text, home))


def emit(text: str) -> None:
    print(text)


def main(argv: list[str] | None = None) -> int:
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    code, text = perform(args)
    emit(text)
    return code
