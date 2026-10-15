"""A decision is k votes. Confidence is the share that agreed.

A number the model prints after the label is ignored. A stated confidence can
sit on one value for every item, including the ambiguous ones, and then every
threshold behaves the same. The vote share moves. A sample that fails is a
non-vote and it stays in the denominator, so a crash dilutes confidence
instead of disappearing.

Unanimous means all k samples named the same label. Anything less escalates.
Agreement is stability, not proof that the label is true.
"""

from __future__ import annotations


def parse_choose(text: str) -> tuple[list[str], str] | None:
    """`choose yes|no :: the question` -> (options, question)."""
    raw = (text or "").strip()
    if not raw.lower().startswith("choose ") or "::" not in raw:
        return None
    left, body = raw[7:].split("::", 1)
    options = [part.strip() for part in left.split("|") if part.strip()]
    body = body.strip()
    if len(options) < 2 or not body:
        return None
    if len(options) > 12:
        return None
    return options[:12], body[:2000]


def vote_label(raw: str, options: list[str]) -> str | None:
    """First token that is one of the options. A trailing number is not a vote."""
    low = {option.lower(): option for option in options}
    for tok in (raw or "").replace(",", " ").split():
        key = tok.strip(".:'\"%").lower()
        if key in low:
            return low[key]
    return None


def tally(samples: list[str | None], k: int) -> tuple[str | None, float]:
    """Winning label and its share of k. Ties keep the label that appeared first."""
    real = [sample for sample in samples if sample]
    if not real or k <= 0:
        return None, 0.0
    counts: dict[str, int] = {}
    first: dict[str, int] = {}
    for index, label in enumerate(real):
        counts[label] = counts.get(label, 0) + 1
        first.setdefault(label, index)
    win = min(counts, key=lambda label: (-counts[label], first[label]))
    return win, counts[win] / float(k)


def collect(text: str, options: list[str], once, k: int = 3):
    """Ask k times. An exception is a non-vote. Returns label, share, samples."""
    samples: list[str | None] = []
    for _ in range(k):
        try:
            raw = once(text, options)
        except Exception:
            samples.append(None)
            continue
        samples.append(vote_label(str(raw or ""), options))
    label, share = tally(samples, k)
    return label, share, samples


def unanimous(label: str | None, share: float) -> bool:
    return label is not None and share == 1.0
