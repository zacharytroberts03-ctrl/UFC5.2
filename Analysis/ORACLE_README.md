# Oracle — Analysis & Betting AI

This directory contains the betting logic, odds tools, and AI rules for UFC 5.

## Directory Structure

```
Analysis/
├── rules/
│   └── BETTING_AI_RULES.md   # Master rules for Claude AI fight analysis
├── tools/
│   ├── scrape_odds.py         # Live odds fetcher (The Odds API)
│   └── hedge_calculator.py    # Arbitrage & hedge betting math
└── ORACLE_README.md           # This file
```

---

## scrape_odds.py

Fetches live UFC moneyline odds from [The Odds API](https://the-odds-api.com/).

### How it works

1. Calls `GET /v4/sports/mma_mixed_martial_arts/odds` with `regions=us`, `markets=h2h`, `oddsFormat=american`
2. Returns a list of upcoming MMA events, each containing bookmaker odds
3. Fighter matching uses `difflib.SequenceMatcher` fuzzy matching (threshold > 0.7) against `home_team` and `away_team` fields

### Functions

| Function | Purpose |
|---|---|
| `fetch_all_ufc_odds() -> list[dict]` | Returns all upcoming UFC events with moneyline odds from every US bookmaker |
| `find_fight_odds(f1, f2) -> dict or None` | Fuzzy-matches a specific matchup and returns all bookmaker odds, plus best line for each fighter |
| `get_best_lines(f1, f2) -> dict or None` | Convenience wrapper — returns only the best available line per fighter |

### Return shape of `find_fight_odds()`

```python
{
    "fighter1": "Canonical Name A",
    "fighter2": "Canonical Name B",
    "books": [
        {"name": "DraftKings", "f1_odds": -150, "f2_odds": +130},
        {"name": "FanDuel",    "f1_odds": -145, "f2_odds": +125},
    ],
    "best_f1": {"book": "FanDuel", "odds": -145},
    "best_f2": {"book": "DraftKings", "odds": 130},
}
```

---

## hedge_calculator.py

Pure-math module for arbitrage detection and hedge stake calculation. No external dependencies.

### Functions

| Function | Signature | Purpose |
|---|---|---|
| `american_to_decimal` | `(odds: int) -> float` | Convert American odds to decimal. +150 -> 2.50 |
| `american_to_implied` | `(odds: int) -> float` | Convert to implied probability. +150 -> 0.40 |
| `decimal_to_american` | `(decimal_odds: float) -> int` | Reverse conversion |
| `find_arb_pct` | `(f1_odds, f2_odds) -> float` | Arbitrage %. Positive = guaranteed profit |
| `calculate_stakes` | `(f1_odds, f2_odds, total_stake) -> dict` | Optimal stake split for equal profit on both outcomes |
| `best_value_line` | `(odds_list, fighter_key) -> dict` | Find best odds from a list of books |
| `annotate_odds_table` | `(books, f1_name, f2_name) -> list[dict]` | Add best-line flags for UI rendering |
| `summarize_hedge` | `(f1_name, f2_name, odds_data, total_stake) -> dict` | Full hedge summary using cross-book best lines |

### Arb math explained

An arbitrage (arb) exists when the combined implied probability of both fighters across different sportsbooks is less than 100%. This means you can bet on both sides and guarantee a profit regardless of the outcome.

**Example:**
- Book A has Fighter 1 at +150 (implied 40%)
- Book B has Fighter 2 at +130 (implied 43.5%)
- Combined: 83.5% — that leaves 16.5% arb margin

**Equal-profit stake formula:**
```
f1_stake = total_stake * decimal_odds_f2 / (decimal_odds_f1 + decimal_odds_f2)
f2_stake = total_stake * decimal_odds_f1 / (decimal_odds_f1 + decimal_odds_f2)
```

This guarantees the same payout regardless of which fighter wins.

---

## BETTING_AI_RULES.md

Located at `Analysis/rules/BETTING_AI_RULES.md`. This file defines the complete rule set for how Claude must analyze fights and produce betting recommendations.

### Loading into the system prompt

At runtime, read the full contents of `BETTING_AI_RULES.md` and inject it into the Claude system prompt before the fight analysis request. Example:

```python
rules = open("Analysis/rules/BETTING_AI_RULES.md").read()
system_prompt = f"You are a UFC betting analyst. Follow these rules exactly:\n\n{rules}"
```

The rules cover five sections:
1. **Fight Analysis** — how to compare stats, derive styles, handle missing data
2. **Output Format** — required HTML comment markers and section structure
3. **Betting Recommendations** — the exact template for the BETTING section
4. **Line Value** — how to assess whether odds represent value
5. **Hedge Betting** — when to hedge, when not to, and how to calculate stakes

---

## Required Environment Variable

| Variable | Source | Notes |
|---|---|---|
| `ODDS_API_KEY` | [theOddsAPI.com](https://the-odds-api.com/) | Free tier = 500 requests/month. Set in project root `.env` file. |
