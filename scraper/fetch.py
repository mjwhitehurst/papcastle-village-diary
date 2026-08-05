"""
Live glue for the scraper: fetch the 'Other Documents' page, pull the
newsletter links out of it, and extract text from a chosen PDF.

Kept separate from the parsing logic (newsletters.py / diary.py) so the fragile,
well-tested pure functions never depend on the network. This module is the only
part that talks to the outside world.
"""

import io
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import pdfplumber

from newsletters import issue_number

BASE = "https://www.papcastleparishcouncil.gov.uk/"
DOCS_URL = urljoin(BASE, "other-documents/")
UA = "papcastle-village-diary/1.0 (+parish calendar; contact clerk@papcastleparishcouncil.gov.uk)"
_HEADINGS = ("h1", "h2", "h3", "h4")


def fetch_html(url: str = DOCS_URL) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.text


def _clean_link_text(text: str) -> str:
    """The site appends a screen-reader 'Opens in a new tab' span to each link,
    and the extracted text has doubled spaces. Both end up in the issue title."""
    text = re.sub(r"\s*opens in a new (tab|window)\s*$", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def newsletter_links(html: str, base: str = BASE) -> list[tuple[str, str]]:
    """Return (link_text, absolute_url) for every newsletter link.

    Scopes to the 'Newsletters' section (heading -> next same-or-higher heading),
    then keeps only links that actually parse to an issue number. The second
    filter means we still work even if the page's heading structure shifts.
    """
    soup = BeautifulSoup(html, "html.parser")

    start = next((h for h in soup.find_all(_HEADINGS)
                  if h.get_text(strip=True).lower().startswith("newsletter")), None)

    if start is not None:
        level = start.name
        scoped: list = []
        for el in start.find_all_next():
            # Stop at the next section heading of the same or higher level.
            if el.name in _HEADINGS and el.name <= level and el is not start:
                break
            if el.name == "a" and el.get("href"):
                scoped.append(el)
        anchors = scoped
    else:
        anchors = soup.find_all("a", href=True)  # fallback: whole page

    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in anchors:
        text = _clean_link_text(a.get_text(" ", strip=True))
        href = urljoin(base, a["href"])
        if href in seen:
            continue
        if issue_number(text) is not None:   # guard: only real newsletters
            links.append((text, href))
            seen.add(href)
    return links


def issue_year(title: str, fallback: int) -> int:
    """Best-effort publication year from a title like '... Spring 2026'."""
    m = re.search(r"(19|20)\d{2}", title)
    return int(m.group(0)) if m else fallback


def pdf_text(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)
