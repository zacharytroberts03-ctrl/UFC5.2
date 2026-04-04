"""
Tool: scrape_ufc_card.py
Purpose: Scrape the next upcoming UFC event from ufcstats.com and return
         the full fight card as a structured dict.

Usage:
  python tools/scrape_ufc_card.py             # prints next event + fights
  python tools/scrape_ufc_card.py --debug     # also prints raw FireCrawl markdown
"""

import os
import re
import sys
import time
import json

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

from dotenv import load_dotenv
load_dotenv()

from firecrawl import Firecrawl

DELAY = 2  # seconds between FireCrawl requests


def _get_firecrawl():
    """Create a Firecrawl client using the current environment key."""
    key = os.getenv("FIRECRAWL_API_KEY")
    if not key:
        raise EnvironmentError("FIRECRAWL_API_KEY not set. Add it to your Streamlit secrets.")
    return Firecrawl(api_key=key)


# ── FireCrawl helper ──────────────────────────────────────────────────────────

def firecrawl_get(url: str) -> str:
    """Scrape a URL with FireCrawl and return markdown. Retries once on 429."""
    client = _get_firecrawl()
    try:
        result = client.scrape(url, formats=["markdown"])
        return result.markdown or ""
    except Exception as e:
        err = str(e)
        if "429" in err or "rate" in err.lower():
            print("  Rate limited. Waiting 10s then retrying...")
            time.sleep(10)
            result = client.scrape(url, formats=["markdown"])
            return result.markdown or ""
        raise


# ── Upcoming events page parser ───────────────────────────────────────────────

def parse_upcoming_event(markdown: str, debug: bool = False) -> tuple[str, str, str, str]:
    """
    Parse the first upcoming event from the events list page.
    Returns (event_name, date, location, event_url).

    Confirmed ufcstats format (FireCrawl markdown):
      | _[Event Name](http://www.ufcstats.com/event-details/UUID)_<br>_Date_ | Location |
    Event name + date are in the SAME cell, separated by <br>.
    """
    if debug:
        print("\n--- RAW UPCOMING EVENTS MARKDOWN (first 5000 chars) ---")
        print(markdown[:5000])
        print("--- END ---\n")

    # Combined pattern: captures event name, URL, date, and location from one row
    row_pattern = re.compile(
        r'\|\s*_?\[([^\]]+)\]\((http://www\.ufcstats\.com/event-details/[a-f0-9]+)\)_?'
        r'<br>_([^_\n|]+)_?\s*\|\s*([^|\n]+?)\s*\|',
        re.IGNORECASE
    )

    m = row_pattern.search(markdown)
    if not m:
        raise ValueError(
            "No upcoming event found on ufcstats.com/statistics/events/upcoming.\n"
            "Run with --debug to inspect the raw markdown."
        )

    event_name = re.sub(r'[_*`]', '', m.group(1)).strip()
    event_url  = m.group(2).strip()
    date       = re.sub(r'[_*`]', '', m.group(3)).strip()
    location   = re.sub(r'[_*`]', '', m.group(4)).strip()

    return event_name, date, location, event_url


# ── Event details page parser ─────────────────────────────────────────────────

def parse_fight_card(markdown: str, debug: bool = False) -> list[dict]:
    """
    Parse all fights from an event details page.
    Returns list of {fighter1, fighter2, weight_class} dicts.

    Confirmed format: [Fighter1](url)<br>[Fighter2](url) in same table cell,
    with weight class as plain text in the same row.
    """
    if debug:
        print("\n--- RAW EVENT DETAILS MARKDOWN (first 8000 chars) ---")
        print(markdown[:8000])
        print("--- END ---\n")

    fights = []

    weight_classes = [
        "Strawweight", "Flyweight", "Bantamweight", "Featherweight",
        "Lightweight", "Welterweight", "Middleweight", "Light Heavyweight",
        "Heavyweight", "Women's Strawweight", "Women's Flyweight",
        "Women's Bantamweight", "Women's Featherweight"
    ]
    weight_pattern = re.compile(
        r'(' + '|'.join(re.escape(w) for w in weight_classes) + r')',
        re.IGNORECASE
    )

    fighter_pair_pattern = re.compile(
        r'\[([^\]]+)\]\(http://www\.ufcstats\.com/fighter-details/[a-f0-9]+\)'
        r'<br>'
        r'\[([^\]]+)\]\(http://www\.ufcstats\.com/fighter-details/[a-f0-9]+\)',
        re.IGNORECASE
    )

    lines = markdown.split('\n')
    for line in lines:
        m = fighter_pair_pattern.search(line)
        if not m:
            continue

        f1 = re.sub(r'[_*`]', '', m.group(1)).strip()
        f2 = re.sub(r'[_*`]', '', m.group(2)).strip()

        if not f1 or not f2 or f1.lower() == f2.lower():
            continue

        wm = weight_pattern.search(line)
        weight_class = wm.group(1) if wm else "N/A"

        fights.append({
            "fighter1": f1,
            "fighter2": f2,
            "weight_class": weight_class,
        })

    # Fallback: any two fighter links close together on the same line
    if not fights:
        vs_pattern = re.compile(
            r'\[([^\]]+)\]\(http://www\.ufcstats\.com/fighter-details/[a-f0-9]+\)'
            r'[^\n]{0,30}'
            r'\[([^\]]+)\]\(http://www\.ufcstats\.com/fighter-details/[a-f0-9]+\)',
            re.IGNORECASE
        )
        seen = set()
        for m in vs_pattern.finditer(markdown):
            f1 = re.sub(r'[_*`]', '', m.group(1)).strip()
            f2 = re.sub(r'[_*`]', '', m.group(2)).strip()
            key = (f1.lower(), f2.lower())
            if key in seen or not f1 or not f2 or f1.lower() == f2.lower():
                continue
            seen.add(key)
            fights.append({"fighter1": f1, "fighter2": f2, "weight_class": "N/A"})

    return fights


# ── Main scrape function ──────────────────────────────────────────────────────

def scrape_upcoming_card(debug: bool = False) -> dict:
    """
    Scrape the next upcoming UFC event from ufcstats.com.
    Returns a dict with event info and the full fight card.
    """
    print("Fetching upcoming UFC event list...")
    events_url = "http://www.ufcstats.com/statistics/events/upcoming"
    events_md = firecrawl_get(events_url)
    time.sleep(DELAY)

    event_name, date, location, event_url = parse_upcoming_event(events_md, debug=debug)
    print(f"  Found: {event_name} — {date}")
    print(f"  URL: {event_url}")

    print(f"Fetching fight card...")
    card_md = firecrawl_get(event_url)
    time.sleep(DELAY)

    fights = parse_fight_card(card_md, debug=debug)
    print(f"  Parsed {len(fights)} fights")

    return {
        "event_name": event_name,
        "date": date,
        "location": location,
        "event_url": event_url,
        "fights": fights,
    }


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    debug_mode = "--debug" in sys.argv

    card = scrape_upcoming_card(debug=debug_mode)

    print()
    print(f"=== {card['event_name']} ===")
    print(f"Date:     {card['date']}")
    print(f"Location: {card['location']}")
    print()
    for i, fight in enumerate(card["fights"], 1):
        wc = f" [{fight['weight_class']}]" if fight['weight_class'] != "N/A" else ""
        print(f"  {i:2}. {fight['fighter1']} vs {fight['fighter2']}{wc}")

    if not card["fights"]:
        print("  (no fights parsed — run with --debug to inspect raw markdown)")
