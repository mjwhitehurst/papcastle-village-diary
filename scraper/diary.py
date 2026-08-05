"""
Parse 'diary dates' out of a Villager newsletter's extracted text.

The text does NOT come out as a clean table. Events appear as blocks anchored
on a date (or 'Every <weekday>'), running until the next anchor. In the real
PDFs the diary is a two-column table, so pdfplumber puts the anchor and the
title on ONE line and the time and more description on the next:

    Every Monday      Keep Fit in the Village Hall. Suspended until Autumn.
    6.30 - 7.30 pm    Tony for further details - tony.magorrian@googlemail.com

Older/reflowed text puts each field on its own line, so we take the title from
the anchor line when there is one and fall back to scanning the block when
there isn't. Dates carry weekday prefixes and ordinal suffixes and no year, so
we infer the year from the issue.

This is deliberately a best-effort deterministic pass. Everything it produces
is marked needs_review=True by default so a human approves before publish; an
optional LLM pass (see refine_with_llm stub) can clean up the messy ones.
"""

import re
from dataclasses import dataclass, field, asdict

MONTHS = ("January February March April May June July August September "
          "October November December").split()
_MONTH_NUM = {m.lower(): i for i, m in enumerate(MONTHS, 1)}
_WEEKDAYS = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
_WD = "|".join(_WEEKDAYS)
_MO = "|".join(MONTHS)

# One-off date, e.g. 'Friday, 8th May' / 'Saturday 18th July' / '4th July'.
_DATE = re.compile(
    rf"^(?:(?:{_WD}),?\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MO})\b", re.I)
# Recurring, e.g. 'Every Thursday*'.
_RECUR = re.compile(rf"^Every\s+({_WD})\b", re.I)
# Times: '7.00 pm', '6.30 - 7.30 pm', '2-5 pm', or 'Class times vary'.
_TIME = re.compile(
    r"(\d{1,2}[.:]\d{2}\s*(?:am|pm)?(?:\s*[-–]\s*\d{1,2}[.:]?\d{0,2}\s*(?:am|pm))?"
    r"|\d{1,2}\s*[-–]\s*\d{1,2}\s*(?:am|pm)"
    r"|\d{1,2}\s*(?:am|pm)"
    r"|class times vary)", re.I)
# Trailing clauses that are contact details, not part of the title.
_META = re.compile(r"@|\d{5,}|^(?:with|contact|tel)\b", re.I)
# A diary-table row always carries a time, price, phone, email or a note
# marker; village-news prose after the table does not.
_CONT_CUE = re.compile(r"[\d@£]|^\s*[(*]")


@dataclass
class Event:
    title: str
    kind: str                       # 'one_off' or 'recurring'
    date: str | None = None         # ISO 'YYYY-MM-DD' for one-offs
    weekday: str | None = None      # for recurring
    time_text: str | None = None
    notes: str = ""
    raw: str = ""
    needs_review: bool = True


def _is_anchor(line: str) -> bool:
    s = line.strip()
    if not s or s[0] in "(*":        # '(no classes...)' and '* Wednesday...' are notes
        return False
    return bool(_RECUR.match(s) or _DATE.match(s))


def _find_time(lines: list[str]) -> str | None:
    for ln in lines:
        m = _TIME.search(ln)
        if m:
            return m.group(0).strip()
    return None


def _find_title(lines: list[str]) -> str:
    """First substantive line that isn't the time. Used only when the anchor
    line carries no inline title (the one-field-per-line layout)."""
    for ln in lines:
        s = ln.strip()
        if not s or _TIME.fullmatch(s) or _TIME.match(s):
            continue
        return _clean_title(s)
    return "(untitled)"


def _is_decoration(clause: str) -> bool:
    """'SAVE THE DATE', 'ADVANCE NOTICE' — shouty prefixes, not the event."""
    letters = [c for c in clause if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters) and len(clause) <= 30


def _clean_title(text: str) -> str:
    """Title out of a run of table text: first sentence, minus the contact
    details the volunteers append and minus any 'SAVE THE DATE -' prefix."""
    s = re.split(r"[.!?]", text.strip(" *-–\t"))[0]
    parts = [p.strip() for p in re.split(r"\s+[-–]\s+", s) if p.strip()]
    while len(parts) > 1 and _META.search(parts[-1]):
        parts.pop()
    if len(parts) > 1 and _is_decoration(parts[0]):
        parts.pop(0)
    return " - ".join(parts).strip(" -–!") or "(untitled)"


def _diary_section(lines: list[str]) -> list[str]:
    """Narrow the whole newsletter down to the diary table.

    A Villager is a magazine: articles routinely open with a date ('Friday 12th
    June the hall was...'), so parsing the full text invents events. Start after
    the 'Diary Dates' heading and stop once the lines stop looking like table
    rows. If there's no heading the text is already just the table (a fixture),
    so use it as-is.
    """
    start = next((i + 1 for i, ln in enumerate(lines)
                  if "diarydates" in re.sub(r"\s+", "", ln).lower()), None)
    if start is None:
        return lines

    end, seen_anchor = len(lines), False
    for i in range(start, len(lines)):
        if _is_anchor(lines[i]):
            seen_anchor = True
        elif seen_anchor and lines[i].strip() and not _CONT_CUE.search(lines[i]):
            end = i
            break
    return lines[start:end]


def parse_events(text: str, issue_year: int) -> list[Event]:
    lines = _diary_section([ln.rstrip() for ln in text.splitlines()])
    # Locate anchors, then slice each block up to the next anchor.
    idx = [i for i, ln in enumerate(lines) if _is_anchor(ln)]
    events: list[Event] = []
    for a, start in enumerate(idx):
        end = idx[a + 1] if a + 1 < len(idx) else len(lines)
        anchor = lines[start].strip()
        block = lines[start:end]
        body = block[1:]                       # lines after the anchor
        time_text = _find_time(body)
        raw = " / ".join(x.strip() for x in block if x.strip())

        rec = _RECUR.match(anchor)
        dm = rec or _DATE.match(anchor)
        inline = anchor[dm.end():]             # two-column layout: title sits here
        title = _clean_title(inline) if inline.strip() else _find_title(body)

        if rec:
            events.append(Event(
                title=title, kind="recurring", weekday=rec.group(1).title(),
                time_text=time_text, raw=raw))
            continue

        day = int(dm.group(1))
        month = _MONTH_NUM[dm.group(2).lower()]
        iso = f"{issue_year:04d}-{month:02d}-{day:02d}"
        events.append(Event(
            title=title, kind="one_off", date=iso,
            time_text=time_text, raw=raw))
    return events


def refine_with_llm(events: list[Event], full_text: str) -> list[Event]:
    """Optional second pass. Send the raw blocks to an LLM to correct titles,
    split recurring exceptions, and fix year roll-over, returning structured
    JSON. Left as a stub; deterministic output already covers the common case."""
    return events


def to_dicts(events: list[Event]) -> list[dict]:
    return [asdict(e) for e in events]
