"""
Tool: scrape_debut_fighter.py
Purpose: When a fighter is not found on ufcstats.com (typically a UFC debutant),
         search Tapology for their professional MMA record and fight history.

Returns the same dict structure as scrape_ufc_fighter.scrape_fighter(), but with:
  - ufc_debut: True
  - debut_source: "Tapology"
  - striking/grappling per-minute averages all N/A (UFC-computed stats, unavailable)

Usage:
  python tools/scrape_debut_fighter.py "Fighter Name"
"""

import os
import re
import sys
import time
import json
import urllib.parse
from firecrawl import Firecrawl
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

load_dotenv()

DELAY = 2


def _get_firecrawl():
    key = os.getenv("FIRECRAWL_API_KEY")
    if not key:
        raise EnvironmentError("FIRECRAWL_API_KEY not set.")
    return Firecrawl(api_key=key)


def firecrawl_get(url: str) -> str:
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


# ── Tapology search ───────────────────────────────────────────────────────────

def find_on_tapology(name: str) -> tuple[str, str]:
    """
    Search Tapology for the fighter. Returns (profile_url, matched_name).
    Raises ValueError if not found.
    """
    search_url = (
        "https://www.tapology.com/search"
        f"?term={urllib.parse.quote(name)}&model=fighters"
    )
    print(f"  Searching Tapology: {search_url}")
    md = firecrawl_get(search_url)
    time.sleep(DELAY)

    if not md:
        raise ValueError(f'"{name}": empty response from Tapology search.')

    # Profile links: absolute or relative, e.g. /fightcenter/fighters/12345-jon-jones
    link_pattern = re.compile(
        r'\[([^\]\n]+)\]\(((?:https?://(?:www\.)?tapology\.com)?/fightcenter/fighters/\d+[^\s\)]*)\)',
        re.IGNORECASE,
    )
    matches = link_pattern.findall(md)

    if not matches:
        raise ValueError(f'"{name}" not found on Tapology.')

    name_lower = name.strip().lower()
    input_words = set(name_lower.split())

    # 1. Exact match on label
    for label, url in matches:
        if label.strip().lower() == name_lower:
            full_url = url if url.startswith("http") else f"https://www.tapology.com{url}"
            return full_url, label.strip()

    # 2. All input words present in label
    partial = [
        (label, url) for label, url in matches
        if input_words.issubset(set(label.strip().lower().split()))
    ]
    if partial:
        label, url = partial[0]
        full_url = url if url.startswith("http") else f"https://www.tapology.com{url}"
        return full_url, label.strip()

    # 3. Last name match
    last = name.strip().split()[-1].lower()
    fuzzy = [(label, url) for label, url in matches if last in label.lower()]
    if fuzzy:
        label, url = fuzzy[0]
        full_url = url if url.startswith("http") else f"https://www.tapology.com{url}"
        return full_url, label.strip()

    # 4. Take first result
    label, url = matches[0]
    full_url = url if url.startswith("http") else f"https://www.tapology.com{url}"
    return full_url, label.strip()


# ── Profile parsing ───────────────────────────────────────────────────────────

def parse_record_tapology(md: str) -> dict:
    """Parse overall MMA record from Tapology profile markdown."""
    # "Record: 15-2-0" or "15-2-0 (W-L-D)" patterns
    for pattern in [
        r'(?:Pro\s+)?(?:MMA\s+)?Record[:\s]+(\d+)[- ](\d+)[- ](\d+)',
        r'\b(\d{1,3})-(\d{1,3})-(\d{1,3})\s*(?:\(W|Win)',
        r'\b(\d{1,3})-(\d{1,3})-(\d{1,3})\b',
    ]:
        m = re.search(pattern, md, re.IGNORECASE)
        if m:
            return {"wins": m.group(1), "losses": m.group(2), "draws": m.group(3)}
    return {"wins": "N/A", "losses": "N/A", "draws": "N/A"}


def parse_stat_tapology(md: str, *labels) -> str:
    """Extract a labeled physical stat from Tapology markdown."""
    for label in labels:
        escaped = re.escape(label)
        # "Height: 6'1"" / "Height | 6'1"" / "**Height** 6'1""
        for pattern in [
            rf'(?:\*\*)?{escaped}(?:\*\*)?\s*[:\|]\s*([^\n\|]+)',
            rf'{escaped}\s+([^\n\|]+)',
        ]:
            m = re.search(pattern, md, re.IGNORECASE)
            if m:
                val = m.group(1).strip().strip('*').strip()
                if val and val not in ('--', '-', 'N/A', ''):
                    return val
    return "N/A"


def parse_fight_history_tapology(md: str, limit: int = 10) -> list[dict]:
    """
    Parse recent fight history from Tapology profile markdown.
    Tapology tables look like:
      | win | Fighter Name | KO/TKO | Organization | Round | Date |
    """
    fights = []

    # Row pattern: result column starts with win/loss/draw/nc
    row_pattern = re.compile(
        r'\|\s*(win|loss|draw|nc|no contest)\s*\|([^\n]+)',
        re.IGNORECASE,
    )

    for m in row_pattern.finditer(md):
        result = m.group(1).strip().upper()
        if result == "NO CONTEST":
            result = "NC"

        rest = m.group(2)
        cells = [c.strip() for c in rest.split("|") if c.strip()]

        # Cell 0 is usually opponent name (may contain a link)
        opponent = "N/A"
        method = "N/A"
        promotion = "N/A"

        if cells:
            opp_raw = cells[0]
            # Strip markdown links: [Name](url) → Name
            opp_clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', opp_raw).strip()
            # Strip bold/italic markers
            opp_clean = re.sub(r'[*_`]', '', opp_clean).strip()
            if opp_clean:
                opponent = opp_clean

        # Look for method in remaining cells
        method_pattern = re.compile(
            r'\b(KO|TKO|Submission|Sub|Decision|U-DEC|S-DEC|Draw|DQ|NC|Unanimous|Split|Majority|Doctor)\b',
            re.IGNORECASE,
        )
        for cell in cells[1:]:
            cell_clean = re.sub(r'\[[^\]]+\]\([^\)]+\)', '', cell).strip()
            mm = method_pattern.search(cell_clean)
            if mm:
                method = cell_clean.split('\n')[0].strip()
                break

        # Look for promotion/org in cells
        for cell in cells:
            cell_clean = re.sub(r'\[[^\]]+\]\([^\)]+\)', '', cell).strip()
            if re.search(r'\b(UFC|Bellator|ONE|PFL|RIZIN|LFA|DWCS|ACB|BAMMA|Invicta|Road to UFC)\b', cell_clean, re.IGNORECASE):
                promotion = cell_clean.strip()
                break

        if opponent and opponent != "N/A":
            fight_entry = {
                "result":    result,
                "opponent":  opponent,
                "method":    method,
                "round":     "N/A",
                "time":      "N/A",
            }
            if promotion != "N/A":
                fight_entry["promotion"] = promotion
            fights.append(fight_entry)

        if len(fights) >= limit:
            break

    return fights


def count_win_methods_from_history(fight_history: list[dict]) -> dict:
    ko = sub = dec = 0
    for f in fight_history:
        if f["result"] != "WIN":
            continue
        method = f.get("method", "").upper()
        if "KO" in method or "TKO" in method:
            ko += 1
        elif "SUB" in method:
            sub += 1
        elif "DEC" in method or "UNANIMOUS" in method or "SPLIT" in method or "MAJORITY" in method:
            dec += 1
    note = f"(from {len(fight_history)} parsed fights)"
    return {"ko": str(ko), "sub": str(sub), "dec": str(dec), "note": f"Counted {note}"}


# ── Main export ───────────────────────────────────────────────────────────────

def scrape_debut_fighter(name: str) -> dict:
    """
    Look up a fighter on Tapology and return a standardized stats dict.
    The dict matches scrape_fighter()'s shape so app.py can use it identically,
    but includes ufc_debut=True and debut_source='Tapology'.

    Raises ValueError if the fighter cannot be found on Tapology either.
    """
    profile_url, matched_name = find_on_tapology(name)
    print(f"  Found on Tapology: {profile_url} (matched: {matched_name})")

    print("  Scraping Tapology profile...")
    md = firecrawl_get(profile_url)
    time.sleep(DELAY)

    record = parse_record_tapology(md)
    fight_history = parse_fight_history_tapology(md)

    # Physical stats — Tapology uses various label formats
    height = parse_stat_tapology(md, "Height", "Ht.")
    weight = parse_stat_tapology(md, "Weight", "Wt.", "Weight Class")
    reach  = parse_stat_tapology(md, "Reach", "Wingspan")
    stance = parse_stat_tapology(md, "Stance", "Fighting Style")
    dob    = parse_stat_tapology(md, "Date of Birth", "Born", "DOB")
    team   = parse_stat_tapology(md, "Gym", "Team", "Affiliation", "Trains at")

    data = {
        "name":        matched_name,
        "profile_url": profile_url,
        "height":      height,
        "weight":      weight,
        "reach":       reach,
        "stance":      stance,
        "dob":         dob,
        "team":        team,
        "record":      record,
        "win_methods": count_win_methods_from_history(fight_history),
        # Per-minute UFC stats are not available for non-UFC fighters
        "striking": {
            "slpm":    "N/A",
            "str_acc": "N/A",
            "sapm":    "N/A",
            "str_def": "N/A",
        },
        "grappling": {
            "td_avg":  "N/A",
            "td_acc":  "N/A",
            "td_def":  "N/A",
            "sub_avg": "N/A",
        },
        "fight_history": fight_history,
        # Debut flags
        "ufc_debut":    True,
        "debut_source": "Tapology",
    }

    wins   = record["wins"]   if record["wins"]   != "N/A" else "?"
    losses = record["losses"] if record["losses"] != "N/A" else "?"
    draws  = record["draws"]  if record["draws"]  != "N/A" else "?"
    print(f"  Scraped debut fighter: {wins}-{losses}-{draws} record, {len(fight_history)} fights parsed")

    return data


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python tools/scrape_debut_fighter.py "Fighter Name"')
        sys.exit(1)

    result = scrape_debut_fighter(sys.argv[1])
    print()
    print(json.dumps(result, indent=2, ensure_ascii=False))
