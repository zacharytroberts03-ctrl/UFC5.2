# UFC 5 Integration — Nexus

## Overview

`app.py` is the main Streamlit application that ties together:

- **UI layer** (`UI/theme.py`, `UI/components.py`) — Premium dark sportsbook theme and reusable HTML components
- **Analysis layer** (`Analysis/tools/scrape_odds.py`, `Analysis/tools/hedge_calculator.py`, `Analysis/rules/BETTING_AI_RULES.md`) — Live odds fetching, arbitrage/hedge math, and AI betting rules
- **Existing tools** (`tools/scrape_ufc_card.py`, `tools/scrape_ufc_fighter.py`, `tools/scrape_debut_fighter.py`) — UFC stats scraping carried over from UFC 4

## Data Flow

```
1. scrape_upcoming_card()        → Event name, date, location, fight list
2. find_fight_odds(f1, f2)       → Multi-book odds, best lines per fighter
3. scrape_fighter(name)          → Fighter stats from ufcstats.com
   └─ scrape_debut_fighter(name) → Tapology fallback for UFC debuts
4. get_analysis(f1, f2)          → Claude AI analysis (claude-sonnet-4-6, 4096 tokens)
   └─ System prompt includes BETTING_AI_RULES.md content
5. summarize_hedge(f1, f2, odds) → Arb detection, optimal stake split, ROI
6. Display via Nova's components  → VS header, odds table, arb banner, hedge card,
                                    analysis sections, betting recommendation
```

## Required Environment Variables

| Variable            | Required | Source                  | Purpose                              |
| ------------------- | -------- | ----------------------- | ------------------------------------ |
| `ANTHROPIC_API_KEY` | Yes      | Anthropic Console       | Claude AI fight analysis             |
| `FIRECRAWL_API_KEY` | Yes      | Firecrawl               | Web scraping (ufcstats, Tapology)    |
| `ODDS_API_KEY`      | No       | the-odds-api.com        | Live sportsbook odds (graceful skip) |

Set these in `.env` for local dev or Streamlit secrets for deployment.

## How to Run

```bash
cd "C:/Users/Owner/Desktop/Claude/AI Websites/UFC 5"
streamlit run app.py
```

## Module Usage

### UI Imports (from Nova)
- `get_css()` — Injected once at startup via `st.markdown()`
- `fighter_vs_header()` — Side-by-side fighter display with photos and moneyline pills
- `odds_comparison_table()` — Multi-book odds grid with best-line highlighting
- `arb_banner()` / `no_arb_banner()` — Green/red arbitrage status banners
- `hedge_result_card()` — Full hedge betting instruction card with amounts
- `analysis_section()` — Gold-bordered AI analysis content block
- `betting_rec_section()` — Gold-accented betting recommendation block
- `event_banner()` — Event header with name, date, location

### Analysis Imports (from Oracle)
- `find_fight_odds(f1, f2)` — Fetches all UFC odds from The Odds API, fuzzy-matches the matchup, returns per-book odds and best lines
- `summarize_hedge(f1, f2, odds_data, stake)` — Runs full hedge calculation using best cross-book lines
- `annotate_odds_table(books, f1, f2)` — Adds `f1_best`/`f2_best` flags for table highlighting
- `calculate_stakes(f1_odds, f2_odds, stake)` — Used for manual odds input fallback

### BETTING_AI_RULES
Loaded from `Analysis/rules/BETTING_AI_RULES.md` at startup and injected into the Claude system prompt. Defines fight analysis format, betting recommendation structure, line value rules, and hedge betting rules.

## Graceful Degradation

| Scenario                    | Behavior                                                        |
| --------------------------- | --------------------------------------------------------------- |
| No `ODDS_API_KEY`           | Odds features silently skip; manual odds input available        |
| `find_fight_odds()` → None  | Shows info message + manual odds input fields                   |
| Fighter not on ufcstats.com | Falls back to `scrape_debut_fighter()` via Tapology             |
| Fighter not found anywhere  | Shows error with spelling suggestion                            |
| Anthropic API error         | Shows specific error (auth vs. generic)                         |
| No fights on card yet       | Shows info message to check back later                          |

## Key Design Notes

- The `_books_for_table()` helper remaps the `"name"` key from scrape_odds output to `"book"` expected by the UI component
- Card data is cached weekly via `@st.cache_data` keyed on `(year, week_number)`
- Fighter images try ESPN API first, then Wikipedia REST API
- Analysis sections are parsed from HTML comment markers (`<!--TAG-->...<!--END-->`)
- The BETTING section is new in UFC 5 (not present in UFC 4)
