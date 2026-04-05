"""
Tool: scrape_ufc_fighter.py
Purpose: Given a UFC fighter's name, search ufcstats.com, find their profile,
         and return structured stats data as a dict (or JSON if run directly).

Uses direct HTTP requests — no Firecrawl required.

Usage:
  python tools/scrape_ufc_fighter.py "Jon Jones"
  python tools/scrape_ufc_fighter.py "Jon Jones" --debug
"""

import os
import re
import sys
import time
import json

import requests

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
TIMEOUT = 15
DELAY = 1


def _get(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


# ── Fighter search ───────────────────────────────────────────────────────────

def find_fighter_url(name: str, debug: bool = False) -> tuple[str, str]:
    """
    Search ufcstats.com for a fighter by name.
    Returns (profile_url, matched_full_name).
    Raises ValueError if not found.
    """
    parts = name.strip().split()
    last_initial = parts[-1][0].lower() if parts else "a"

    search_url = f"http://www.ufcstats.com/statistics/fighters?char={last_initial}&page=all"
    print(f"  Searching: {search_url}")

    html = _get(search_url)
    time.sleep(DELAY)

    if debug:
        print("\n--- RAW SEARCH HTML (first 3000 chars) ---")
        print(html[:3000])
        print("--- END ---\n")

    # Each fighter row has: first name cell, last name cell, nickname cell — all same URL
    row_pattern = re.compile(
        r'<tr[^>]*class="b-statistics__table-row"[^>]*>(.*?)</tr>',
        re.DOTALL,
    )
    link_pattern = re.compile(
        r'<a[^>]+href="(http://www\.ufcstats\.com/fighter-details/[a-f0-9]+)"[^>]*>\s*([^<\n]+?)\s*</a>'
    )

    candidates: list[tuple[str, str]] = []  # (url, full_name)
    seen_urls: set[str] = set()

    for row_match in row_pattern.finditer(html):
        row_html = row_match.group(1)
        links = link_pattern.findall(row_html)
        if not links:
            continue

        # All links in the row share the same URL; first = first name, second = last name
        url = links[0][0]
        if url in seen_urls:
            continue
        seen_urls.add(url)

        first = links[0][1].strip() if len(links) > 0 else ""
        last  = links[1][1].strip() if len(links) > 1 else ""
        full  = f"{first} {last}".strip()

        if full:
            candidates.append((url, full))

    if not candidates:
        raise ValueError(
            f'Fighter "{name}" not found — no fighters parsed from search page.\n'
            f'Run with --debug to inspect raw HTML.'
        )

    name_lower = name.strip().lower()
    input_words = set(name_lower.split())

    # 1. Exact full-name match
    for url, full in candidates:
        if full.lower() == name_lower:
            return url, full

    # 2. All input words present
    partial = [(url, full) for url, full in candidates
               if input_words.issubset(set(full.lower().split()))]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        return min(partial, key=lambda x: len(x[1]))

    # 3. Last name contains match
    last_word = parts[-1].lower()
    fuzzy = [(url, full) for url, full in candidates if last_word in full.lower()]
    if fuzzy:
        return fuzzy[0]

    raise ValueError(
        f'Fighter "{name}" not found on ufcstats.com.\n'
        f'Tip: check spelling, try full name (e.g., "Jon Jones").'
    )


# ── Stat parsing ─────────────────────────────────────────────────────────────

def parse_stat_html(html: str, *labels) -> str:
    """Extract a labeled stat value from the fighter profile HTML."""
    for label in labels:
        pattern = re.compile(
            r'<i[^>]*>\s*' + re.escape(label) + r'\s*</i>\s*([^<\n]+?)\s*</li>',
            re.IGNORECASE | re.DOTALL,
        )
        m = pattern.search(html)
        if m:
            val = m.group(1).strip()
            if val and val not in ('--', '-', ''):
                return val
    return "N/A"


def parse_record(html: str) -> dict:
    """Parse W-L-D record from fighter profile HTML."""
    # ufcstats shows record like: <span class="b-content__title-record">Record: 20-7-1</span>
    m = re.search(r'Record:\s*(\d+)-(\d+)-(\d+)', html, re.IGNORECASE)
    if m:
        return {"wins": m.group(1), "losses": m.group(2), "draws": m.group(3)}
    # Fallback: bare N-N-N near the top of page
    m = re.search(r'\b(\d+)-(\d+)-(\d+)\b', html[:5000])
    if m:
        return {"wins": m.group(1), "losses": m.group(2), "draws": m.group(3)}
    return {"wins": "N/A", "losses": "N/A", "draws": "N/A"}


def count_win_methods(fight_history: list[dict]) -> dict:
    ko = sub = dec = 0
    for f in fight_history:
        if f["result"] != "WIN":
            continue
        method = f.get("method", "").upper()
        if "KO" in method or "TKO" in method:
            ko += 1
        elif "SUB" in method:
            sub += 1
        elif "DEC" in method:
            dec += 1
    return {
        "ko":   str(ko),
        "sub":  str(sub),
        "dec":  str(dec),
        "note": f"(last {len(fight_history)} fights)",
    }


def parse_fight_history(html: str, fighter_url: str, limit: int = 10) -> list[dict]:
    """Parse recent fight history from the fighter profile HTML."""
    fights = []

    row_pattern = re.compile(
        r'<tr[^>]*class="b-fight-details__table-row[^"]*js-fight-details-click[^"]*"[^>]*>(.*?)</tr>',
        re.DOTALL,
    )

    for row_match in row_pattern.finditer(html):
        row_html = row_match.group(1)

        # Result: win / loss / draw / nc
        result_m = re.search(r'<i[^>]*class="b-flag__text"[^>]*>(\w+)', row_html, re.IGNORECASE)
        if not result_m:
            continue
        result = result_m.group(1).strip().upper()

        # Fighter links — two per row (self + opponent); opponent is the other URL
        fighter_links = re.findall(
            r'<a[^>]+href="(http://www\.ufcstats\.com/fighter-details/[a-f0-9]+)"[^>]*>\s*([^<\n]+?)\s*</a>',
            row_html,
        )
        opponent = "N/A"
        for url, fname in fighter_links:
            if url != fighter_url:
                opponent = fname.strip()
                break

        # Extract all <p> text values (plain text cells)
        p_texts = re.findall(
            r'<p[^>]*class="b-fight-details__table-text"[^>]*>\s*(.*?)\s*</p>',
            row_html,
            re.DOTALL,
        )
        plain = [re.sub(r'<[^>]+>', '', t).strip() for t in p_texts]
        plain = [v for v in plain if v]

        # Method, round, time are near the end of the row
        method = "N/A"
        round_num = "N/A"
        time_str = "N/A"

        for val in reversed(plain):
            if re.match(r'^\d:\d\d$|^\d:\d\d\d$|^\d+:\d\d$', val):
                time_str = val
            elif re.match(r'^\d$', val) and round_num == "N/A":
                round_num = val
            elif re.match(r'(KO|TKO|SUB|U-DEC|S-DEC|M-DEC|Decision|Overturned|DQ|NC)', val, re.IGNORECASE):
                method = val
                break

        if opponent and opponent != "N/A":
            fights.append({
                "result":   result,
                "opponent": opponent,
                "method":   method,
                "round":    round_num,
                "time":     time_str,
            })

        if len(fights) >= limit:
            break

    return fights


# ── Main scrape function ──────────────────────────────────────────────────────

def scrape_fighter(name: str, debug: bool = False) -> dict:
    """
    Given a fighter name, scrape ufcstats.com and return a structured stats dict.
    """
    print(f"Fetching data for {name}...")

    profile_url, matched_name = find_fighter_url(name, debug=debug)
    print(f"  Found profile: {profile_url}")

    print("  Scraping stats...")
    html = _get(profile_url)
    time.sleep(DELAY)

    if debug:
        print("\n--- RAW PROFILE HTML (first 5000 chars) ---")
        print(html[:5000])
        print("--- END ---\n")

    record = parse_record(html)
    fight_history = parse_fight_history(html, profile_url)

    data = {
        "name":        matched_name,
        "profile_url": profile_url,
        "height":      parse_stat_html(html, "Height:"),
        "weight":      parse_stat_html(html, "Weight:"),
        "reach":       parse_stat_html(html, "Reach:"),
        "stance":      parse_stat_html(html, "STANCE:", "Stance:"),
        "dob":         parse_stat_html(html, "DOB:"),
        "team":        "N/A — not listed on ufcstats.com",
        "record":      record,
        "win_methods": count_win_methods(fight_history),
        "striking": {
            "slpm":    parse_stat_html(html, "SLpM:"),
            "str_acc": parse_stat_html(html, "Str. Acc.:"),
            "sapm":    parse_stat_html(html, "SApM:"),
            "str_def": parse_stat_html(html, "Str. Def:"),
        },
        "grappling": {
            "td_avg":  parse_stat_html(html, "TD Avg.:"),
            "td_acc":  parse_stat_html(html, "TD Acc.:"),
            "td_def":  parse_stat_html(html, "TD Def.:"),
            "sub_avg": parse_stat_html(html, "Sub. Avg.:"),
        },
        "fight_history": fight_history,
    }

    wins   = record["wins"]   if record["wins"]   != "N/A" else "?"
    losses = record["losses"] if record["losses"] != "N/A" else "?"
    draws  = record["draws"]  if record["draws"]  != "N/A" else "?"
    print(f"  Scraped: {wins}-{losses}-{draws} record, {len(fight_history)} fights parsed")

    return data


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python tools/scrape_ufc_fighter.py "Fighter Name" [--debug]')
        sys.exit(1)

    fighter_name = sys.argv[1]
    debug_mode = "--debug" in sys.argv

    result = scrape_fighter(fighter_name, debug=debug_mode)
    print()
    print(json.dumps(result, indent=2, ensure_ascii=False))
