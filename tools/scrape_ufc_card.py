"""
Tool: scrape_ufc_card.py
Purpose: Scrape the next upcoming UFC event from ufcstats.com and return
         the full fight card as a structured dict.

Uses direct HTTP requests — no Firecrawl required.

Usage:
  python tools/scrape_ufc_card.py             # prints next event + fights
  python tools/scrape_ufc_card.py --debug     # also prints raw HTML snippet
"""

import os
import re
import sys
import time
import datetime

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
TIMEOUT = 15
DELAY = 1  # seconds between requests


def _get(url: str) -> str:
    """Fetch a URL and return the HTML text."""
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


# ── Event list parser (shared by upcoming + completed pages) ──────────────────

def _parse_date(date_str: str) -> datetime.date | None:
    """Parse 'Month DD, YYYY' into a date object."""
    try:
        return datetime.datetime.strptime(date_str.strip(), "%B %d, %Y").date()
    except ValueError:
        return None


def _parse_event_list(html: str) -> list[dict]:
    """
    Parse all events from an ufcstats event list page.
    Returns list of {name, url, date_str, date, location}.
    """
    event_pattern = re.compile(
        r'<a[^>]+href="(http://www\.ufcstats\.com/event-details/[a-f0-9]+)"[^>]*>\s*([^<\n]+?)\s*</a>'
        r'.*?<span[^>]*class="b-statistics__date"[^>]*>\s*([^<\n]+?)\s*</span>',
        re.DOTALL,
    )

    events = []
    for m in event_pattern.finditer(html):
        url       = m.group(1).strip()
        name      = re.sub(r'\s+', ' ', m.group(2)).strip()
        date_str  = re.sub(r'\s+', ' ', m.group(3)).strip()
        date      = _parse_date(date_str)

        # Location: next <td> after this match
        next_td = re.search(r'<td[^>]*>(.*?)</td>', html[m.end():], re.DOTALL)
        if next_td:
            loc_text = re.sub(r'<[^>]+>', '', next_td.group(1)).strip()
            location = re.sub(r'\s+', ' ', loc_text).strip() or "N/A"
        else:
            location = "N/A"

        events.append({
            "name": name,
            "url": url,
            "date_str": date_str,
            "date": date,
            "location": location,
        })

    return events


def find_current_event(debug: bool = False) -> tuple[str, str, str, str]:
    """
    Find the most relevant event: today's event if one exists, otherwise
    the next upcoming event. Checks both completed and upcoming pages.
    Returns (event_name, date, location, event_url).
    """
    today = datetime.date.today()

    # Pull both pages
    upcoming_html   = _get("http://www.ufcstats.com/statistics/events/upcoming")
    completed_html  = _get("http://www.ufcstats.com/statistics/events/completed")

    upcoming_events  = _parse_event_list(upcoming_html)
    completed_events = _parse_event_list(completed_html)

    all_events = upcoming_events + completed_events

    if not all_events:
        raise ValueError("No events found on ufcstats.com.")

    # Priority 1: event happening today
    for ev in all_events:
        if ev["date"] == today:
            return ev["name"], ev["date_str"], ev["location"], ev["url"]

    # Priority 2: most recent past event (closest to today going backward)
    past = [ev for ev in all_events if ev["date"] and ev["date"] < today]
    if past:
        closest = max(past, key=lambda e: e["date"])
        return closest["name"], closest["date_str"], closest["location"], closest["url"]

    # Priority 3: next future event (closest upcoming)
    future = [ev for ev in all_events if ev["date"] and ev["date"] > today]
    if future:
        closest = min(future, key=lambda e: e["date"])
        return closest["name"], closest["date_str"], closest["location"], closest["url"]

    raise ValueError("Could not determine a current or upcoming UFC event.")


# ── Event details page parser ─────────────────────────────────────────────────

def parse_fight_card(html: str, debug: bool = False) -> list[dict]:
    """
    Parse all fights from an event details page.
    Returns list of {fighter1, fighter2, weight_class} dicts.
    """
    if debug:
        print("\n--- EVENT DETAILS HTML (first 5000 chars) ---")
        print(html[:5000])
        print("--- END ---\n")

    fights = []
    seen = set()

    weight_classes = [
        "Strawweight", "Flyweight", "Bantamweight", "Featherweight",
        "Lightweight", "Welterweight", "Middleweight", "Light Heavyweight",
        "Heavyweight", "Women's Strawweight", "Women's Flyweight",
        "Women's Bantamweight", "Women's Featherweight",
    ]
    weight_pattern = re.compile(
        r'(' + '|'.join(re.escape(w) for w in weight_classes) + r')',
        re.IGNORECASE,
    )

    # Each fight row is a <tr class="b-fight-details__table-row ...">
    row_pattern = re.compile(
        r'<tr[^>]*class="b-fight-details__table-row[^"]*js-fight-details-click[^"]*"[^>]*>(.*?)</tr>',
        re.DOTALL,
    )

    # Fighter names are in consecutive <a> tags within the fighter <td>
    fighter_link_pattern = re.compile(
        r'<a[^>]+href="http://www\.ufcstats\.com/fighter-details/[a-f0-9]+"[^>]*>\s*([^<\n]+?)\s*</a>',
        re.DOTALL,
    )

    for row_match in row_pattern.finditer(html):
        row_html = row_match.group(1)
        fighter_links = fighter_link_pattern.findall(row_html)

        if len(fighter_links) < 2:
            continue

        f1 = re.sub(r'\s+', ' ', fighter_links[0]).strip()
        f2 = re.sub(r'\s+', ' ', fighter_links[1]).strip()

        if not f1 or not f2 or f1.lower() == f2.lower():
            continue

        key = (f1.lower(), f2.lower())
        if key in seen:
            continue
        seen.add(key)

        wm = weight_pattern.search(row_html)
        weight_class = wm.group(1) if wm else "N/A"

        fights.append({
            "fighter1": f1,
            "fighter2": f2,
            "weight_class": weight_class,
        })

    # Fallback: if no js-fight-details-click rows, try any row with two fighter links
    if not fights:
        any_row_pattern = re.compile(
            r'<tr[^>]*class="b-fight-details__table-row[^"]*"[^>]*>(.*?)</tr>',
            re.DOTALL,
        )
        for row_match in any_row_pattern.finditer(html):
            row_html = row_match.group(1)
            fighter_links = fighter_link_pattern.findall(row_html)
            if len(fighter_links) < 2:
                continue
            f1 = re.sub(r'\s+', ' ', fighter_links[0]).strip()
            f2 = re.sub(r'\s+', ' ', fighter_links[1]).strip()
            if not f1 or not f2 or f1.lower() == f2.lower():
                continue
            key = (f1.lower(), f2.lower())
            if key in seen:
                continue
            seen.add(key)
            wm = weight_pattern.search(row_html)
            fights.append({
                "fighter1": f1,
                "fighter2": f2,
                "weight_class": wm.group(1) if wm else "N/A",
            })

    return fights


# ── Main scrape function ──────────────────────────────────────────────────────

def scrape_upcoming_card(debug: bool = False) -> dict:
    """
    Scrape the most current UFC event (today if one exists, otherwise next upcoming).
    Returns a dict with event info and the full fight card.
    """
    print("Finding current UFC event...")
    event_name, date, location, event_url = find_current_event(debug=debug)
    print(f"  Found: {event_name} — {date}")
    print(f"  URL: {event_url}")
    time.sleep(DELAY)

    print("Fetching fight card...")
    card_html = _get(event_url)
    time.sleep(DELAY)

    fights = parse_fight_card(card_html, debug=debug)
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
        print("  (no fights parsed — run with --debug to inspect raw HTML)")
