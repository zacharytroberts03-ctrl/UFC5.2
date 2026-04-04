# UFC 5 Design System

Premium dark sportsbook UI built for Streamlit. Inspired by DraftKings/ESPN Bet aesthetics.

## Quick Start

```python
import streamlit as st
from UI.theme import get_css
from UI.components import fighter_vs_header, odds_comparison_table, arb_banner

# Inject CSS once at app start
st.markdown(get_css(), unsafe_allow_html=True)
```

---

## Color Tokens

| Token            | Hex         | Usage                                    |
| ---------------- | ----------- | ---------------------------------------- |
| Background       | `#0a0a0b`   | App background                           |
| Card surface     | `#13151a`   | Cards, inputs, expanders                 |
| Card border      | `#1e2028`   | Borders, dividers                        |
| Gold accent      | `#d4af37`   | Odds highlights, premium elements        |
| Green profit     | `#00c853`   | Arb banners, wins, guaranteed profit     |
| Red loss         | `#ff1744`   | Losses, no-arb, bad value                |
| UFC red          | `#C8102E`   | Primary buttons, brand accent            |
| Text primary     | `#f0f0f0`   | Headings, strong text                    |
| Text secondary   | `#8a8f9e`   | Labels, muted text                       |
| Text body        | `#d0d0d8`   | Paragraphs, list items                   |
| Font             | Inter        | Weights: 400, 600, 700, 800             |

---

## CSS Classes

### Layout & Streamlit Overrides

| Class / Selector                         | Purpose                          |
| ---------------------------------------- | -------------------------------- |
| `html, body, [data-testid="stApp"]`      | Dark background, Inter font      |
| `[data-testid="stHeader"]`               | Dark header bar                  |
| `.main .block-container`                 | Max-width 1200px container       |

### Custom Components

| Class                 | Purpose                                              |
| --------------------- | ---------------------------------------------------- |
| `.fight-card-banner`  | Event header with gold left border                   |
| `.fighter-vs-block`   | 3-column grid for fighter matchup                    |
| `.fighter-slot`       | Individual fighter card with hover glow              |
| `.vs-divider`         | Gold "VS" text between fighters                      |
| `.moneyline-pill`     | Inline odds badge (`.positive`, `.negative`, `.neutral`) |
| `.odds-table`         | Multi-book odds comparison table                     |
| `.best-line`          | Gold highlight for best available line               |
| `.arb-banner`         | Green gradient arbitrage opportunity banner           |
| `.no-arb-banner`      | Red-tinted no-arbitrage banner                       |
| `.hedge-result-card`  | Hedge betting instruction card                       |
| `.bet-row`            | Flex row inside hedge card                           |
| `.bet-book`           | Muted sportsbook label                               |
| `.bet-amount`         | Gold bet amount                                       |
| `.profit-line`        | Green profit total                                    |
| `.analysis-block`     | AI analysis content section                          |
| `.section-label`      | Gold left-border section heading                     |
| `.confidence-chip`    | Gold badge for confidence percentages                |
| `.betting-rec-block`  | Gold gradient recommendation section                 |
| `.rec-header`         | Uppercase gold header inside rec block               |
| `.debut-badge`        | Gold gradient badge for UFC debuts                   |
| `.odds-updated`       | Flash animation when odds change                     |

---

## Component Functions

All functions live in `components.py` and render via `st.markdown(html, unsafe_allow_html=True)`.

### `fighter_vs_header(f1_name, f2_name, f1_img_url, f2_img_url, f1_odds, f2_odds)`

Side-by-side fighter display with photos (or initial avatars) and moneyline pills.

| Param        | Type          | Description                        |
| ------------ | ------------- | ---------------------------------- |
| `f1_name`    | `str`         | Fighter 1 name                     |
| `f2_name`    | `str`         | Fighter 2 name                     |
| `f1_img_url` | `str \| None` | Fighter 1 photo URL (None = avatar)|
| `f2_img_url` | `str \| None` | Fighter 2 photo URL (None = avatar)|
| `f1_odds`    | `int \| None` | Fighter 1 American odds            |
| `f2_odds`    | `int \| None` | Fighter 2 American odds            |

### `odds_comparison_table(odds_list)`

Multi-sportsbook odds comparison table with best-line highlighting.

| Param       | Type          | Description                                                |
| ----------- | ------------- | ---------------------------------------------------------- |
| `odds_list` | `list[dict]`  | Each dict: `book`, `f1_odds`, `f2_odds`, `f1_best`, `f2_best` |

### `arb_banner(roi_pct, guaranteed_profit, total_stake)`

Green arbitrage opportunity banner.

| Param              | Type    | Description              |
| ------------------ | ------- | ------------------------ |
| `roi_pct`          | `float` | ROI percentage           |
| `guaranteed_profit`| `float` | Guaranteed profit in $   |
| `total_stake`      | `float` | Total combined stake in $|

### `no_arb_banner(best_f1_book, best_f1_odds, best_f2_book, best_f2_odds)`

Red-tinted banner showing best available lines when no arb exists.

| Param          | Type  | Description                  |
| -------------- | ----- | ---------------------------- |
| `best_f1_book` | `str` | Best sportsbook for fighter 1|
| `best_f1_odds` | `int` | Best odds for fighter 1      |
| `best_f2_book` | `str` | Best sportsbook for fighter 2|
| `best_f2_odds` | `int` | Best odds for fighter 2      |

### `hedge_result_card(f1_name, f2_name, f1_stake, f2_stake, f1_book, f2_book, f1_odds, f2_odds, guaranteed_profit, roi_pct)`

Complete hedge betting instruction card with bet amounts and profit.

| Param              | Type    | Description               |
| ------------------ | ------- | ------------------------- |
| `f1_name`          | `str`   | Fighter 1 name            |
| `f2_name`          | `str`   | Fighter 2 name            |
| `f1_stake`         | `float` | Bet amount on fighter 1   |
| `f2_stake`         | `float` | Bet amount on fighter 2   |
| `f1_book`          | `str`   | Sportsbook for fighter 1  |
| `f2_book`          | `str`   | Sportsbook for fighter 2  |
| `f1_odds`          | `int`   | Odds for fighter 1        |
| `f2_odds`          | `int`   | Odds for fighter 2        |
| `guaranteed_profit`| `float` | Guaranteed profit in $    |
| `roi_pct`          | `float` | ROI percentage            |

### `analysis_section(title, content, icon="🥊")`

Analysis content block with gold-bordered section heading.

| Param    | Type  | Description                  |
| -------- | ----- | ---------------------------- |
| `title`  | `str` | Section title                |
| `content`| `str` | HTML content for the block   |
| `icon`   | `str` | Emoji icon prefix (default: boxing glove) |

### `betting_rec_section(content)`

Gold-accented betting recommendation block.

| Param    | Type  | Description                |
| -------- | ----- | -------------------------- |
| `content`| `str` | HTML content for the block |

### `event_banner(event_name, date, location)`

Event header banner with gold accent.

| Param        | Type  | Description        |
| ------------ | ----- | ------------------ |
| `event_name` | `str` | Event title        |
| `date`       | `str` | Event date string  |
| `location`   | `str` | Venue / city       |
