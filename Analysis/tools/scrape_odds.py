"""
scrape_odds.py — Fetch live UFC moneyline odds from The Odds API.

Requires env var: ODDS_API_KEY
API docs: https://the-odds-api.com/loh-odds-api/
"""

import os
import logging
import requests
from difflib import SequenceMatcher
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
BASE_URL = "https://api.the-odds-api.com/v4"
SPORT_KEY = "mma_mixed_martial_arts"


def _name_similarity(a: str, b: str) -> float:
    """Returns 0-1 similarity between two fighter name strings."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def fetch_all_ufc_odds() -> list[dict]:
    """
    Fetches all upcoming UFC MMA events with moneyline odds.
    Returns list of raw event dicts from The Odds API.
    Raises ValueError if API key missing or request fails.
    """
    if not ODDS_API_KEY:
        raise ValueError("ODDS_API_KEY environment variable is not set.")

    url = f"{BASE_URL}/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
    }

    resp = requests.get(url, params=params, timeout=15)

    if resp.status_code == 401:
        raise ValueError("Invalid ODDS_API_KEY — got 401 Unauthorized.")
    if resp.status_code == 422:
        logger.warning("No upcoming MMA events found (422).")
        return []
    if resp.status_code == 429:
        raise ValueError("Rate limited by The Odds API (429). Wait and retry.")

    resp.raise_for_status()
    return resp.json()


def find_fight_odds(fighter1_name: str, fighter2_name: str) -> dict | None:
    """
    Finds odds for a specific matchup by fuzzy-matching fighter names.

    Returns dict:
    {
        "fighter1": str,       # canonical name from API
        "fighter2": str,       # canonical name from API
        "books": [             # list of bookmakers
            {
                "name": str,
                "f1_odds": int,    # American odds for fighter1
                "f2_odds": int,    # American odds for fighter2
            }
        ],
        "best_f1": {"book": str, "odds": int},  # highest odds for f1
        "best_f2": {"book": str, "odds": int},  # highest odds for f2
    }
    Returns None if no match found or API key not set.
    """
    try:
        events = fetch_all_ufc_odds()
    except ValueError as e:
        logger.warning("Could not fetch odds: %s", e)
        return None

    if not events:
        return None

    threshold = 0.7

    for event in events:
        home = event.get("home_team", "")
        away = event.get("away_team", "")

        # Check if fighter1 matches home and fighter2 matches away, or vice versa
        match_a = (
            _name_similarity(fighter1_name, home) > threshold
            and _name_similarity(fighter2_name, away) > threshold
        )
        match_b = (
            _name_similarity(fighter1_name, away) > threshold
            and _name_similarity(fighter2_name, home) > threshold
        )

        if not (match_a or match_b):
            continue

        # Determine canonical mapping
        if match_a:
            canon_f1, canon_f2 = home, away
        else:
            canon_f1, canon_f2 = away, home

        books = []
        best_f1 = {"book": "", "odds": -99999}
        best_f2 = {"book": "", "odds": -99999}

        for bookmaker in event.get("bookmakers", []):
            book_name = bookmaker.get("title", bookmaker.get("key", "Unknown"))
            f1_odds = None
            f2_odds = None

            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                for outcome in market.get("outcomes", []):
                    oname = outcome.get("name", "")
                    price = outcome.get("price")
                    if _name_similarity(oname, canon_f1) > threshold:
                        f1_odds = price
                    elif _name_similarity(oname, canon_f2) > threshold:
                        f2_odds = price

            if f1_odds is not None and f2_odds is not None:
                books.append({
                    "name": book_name,
                    "f1_odds": f1_odds,
                    "f2_odds": f2_odds,
                })
                if f1_odds > best_f1["odds"]:
                    best_f1 = {"book": book_name, "odds": f1_odds}
                if f2_odds > best_f2["odds"]:
                    best_f2 = {"book": book_name, "odds": f2_odds}

        if not books:
            return None

        return {
            "fighter1": canon_f1,
            "fighter2": canon_f2,
            "books": books,
            "best_f1": best_f1,
            "best_f2": best_f2,
        }

    return None


def get_best_lines(fighter1_name: str, fighter2_name: str) -> dict | None:
    """
    Convenience function: returns just the best available line for each fighter.
    Returns {"f1_best": {"book", "odds"}, "f2_best": {"book", "odds"}} or None.
    """
    data = find_fight_odds(fighter1_name, fighter2_name)
    if data is None:
        return None
    return {
        "f1_best": data["best_f1"],
        "f2_best": data["best_f2"],
    }


if __name__ == "__main__":
    import json

    print("Fetching all UFC odds...")
    try:
        all_odds = fetch_all_ufc_odds()
        print(f"Found {len(all_odds)} events.")
        for ev in all_odds:
            print(f"  {ev.get('home_team', '?')} vs {ev.get('away_team', '?')}")
    except ValueError as e:
        print(f"Error: {e}")
