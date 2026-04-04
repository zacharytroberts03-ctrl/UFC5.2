"""
UFC 5 -- UFC Fight Analyzer + Hedge Betting Platform
Browse upcoming UFC cards, get AI-powered fight analysis,
and find guaranteed-profit hedge betting opportunities across sportsbooks.
"""

import os
import re
import sys
import datetime
import requests
import urllib.parse
import streamlit as st
from dotenv import load_dotenv

# -- Load API keys (Streamlit secrets take priority over .env) -----------------
if "FIRECRAWL_API_KEY" in st.secrets:
    os.environ["FIRECRAWL_API_KEY"] = st.secrets["FIRECRAWL_API_KEY"]
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    if "ODDS_API_KEY" in st.secrets:
        os.environ["ODDS_API_KEY"] = st.secrets["ODDS_API_KEY"]
else:
    load_dotenv()

# -- Path setup ----------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(BASE_DIR, "tools"))
sys.path.insert(0, os.path.join(BASE_DIR, "UI"))
sys.path.insert(0, os.path.join(BASE_DIR, "Analysis", "tools"))

# -- Imports -------------------------------------------------------------------
from scrape_ufc_fighter import scrape_fighter
from scrape_debut_fighter import scrape_debut_fighter
from scrape_ufc_card import scrape_upcoming_card
from scrape_odds import find_fight_odds
from hedge_calculator import summarize_hedge, annotate_odds_table, calculate_stakes
from theme import get_css
from components import (
    fighter_vs_header,
    odds_comparison_table,
    arb_banner,
    no_arb_banner,
    hedge_result_card,
    analysis_section,
    betting_rec_section,
    event_banner,
)
import anthropic

# -- Page config ---------------------------------------------------------------
st.set_page_config(
    page_title="UFC Fight Night",
    page_icon="\U0001f94a",
    layout="wide",
)
st.markdown(get_css(), unsafe_allow_html=True)

# -- Load BETTING_AI_RULES ----------------------------------------------------
_RULES_PATH = os.path.join(BASE_DIR, "Analysis", "rules", "BETTING_AI_RULES.md")
with open(_RULES_PATH, "r", encoding="utf-8") as f:
    BETTING_AI_RULES = f.read()

# -- Title ---------------------------------------------------------------------
st.title("\U0001f94a UFC Fight Night")
st.caption(
    "Live stats from ufcstats.com \u00b7 AI analysis by Claude \u00b7 Odds from The Odds API"
)
st.divider()

# -- Session state -------------------------------------------------------------
for key in ["do_analysis", "f1", "f2", "total_stake"]:
    if key not in st.session_state:
        if key == "do_analysis":
            st.session_state[key] = False
        elif key == "total_stake":
            st.session_state[key] = 100.0
        else:
            st.session_state[key] = ""


# -- Helpers -------------------------------------------------------------------

def get_week_key() -> tuple:
    """Returns (year, week_number) -- cache key so card refreshes each Monday."""
    today = datetime.date.today()
    iso = today.isocalendar()
    return (iso[0], iso[1])


@st.cache_data
def load_card_for_week(week_key: tuple) -> dict:
    """Fetch next UFC event, cached per week."""
    return scrape_upcoming_card()


def get_fighter_image(name: str) -> str | None:
    """Fetch a fighter photo. Tries ESPN first, falls back to Wikipedia."""
    headers = {"User-Agent": "UFC-Fight-Night/5.0"}

    # 1. ESPN search API
    try:
        search_url = (
            "https://site.api.espn.com/apis/search/v2"
            f"?query={urllib.parse.quote(name)}&section=mma&limit=5"
        )
        r = requests.get(search_url, timeout=5, headers=headers)
        if r.status_code == 200:
            data = r.json()
            for group in data.get("results", []):
                for item in group.get("contents", []):
                    athlete_id = item.get("id") or item.get("athleteId")
                    if athlete_id:
                        img_url = f"https://a.espncdn.com/i/headshots/mma/players/full/{athlete_id}.png"
                        head = requests.head(img_url, timeout=4, headers=headers)
                        if head.status_code == 200:
                            return img_url
    except Exception:
        pass

    # 2. Wikipedia REST API
    try:
        slug = urllib.parse.quote(name.replace(" ", "_"))
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
            timeout=5,
            headers=headers,
        )
        if r.status_code == 200:
            return r.json().get("thumbnail", {}).get("source")
    except Exception:
        pass

    return None


def yt_highlights_url(name: str) -> str:
    query = urllib.parse.quote(f"{name} UFC recent fights highlights")
    return f"https://www.youtube.com/results?search_query={query}"


def yt_fight_url(fighter: str, opponent: str) -> str:
    query = urllib.parse.quote(f"{fighter} vs {opponent} full fight UFC")
    return f"https://www.youtube.com/results?search_query={query}"


# -- Claude prompt helpers -----------------------------------------------------

SYSTEM_PROMPT = f"""You are an expert UFC analyst and sports betting strategist with deep knowledge of mixed martial arts, fighter styles, matchup dynamics, and line value identification.

{BETTING_AI_RULES}

When analyzing a matchup:
1. Follow all rules in the FIGHT ANALYSIS RULES section above
2. Use the exact output format defined in OUTPUT FORMAT RULES
3. Always include the BETTING section as defined in BETTING RECOMMENDATION RULES
4. Be specific -- cite statistics, not adjectives
5. If stats show N/A (UFC debut), acknowledge the gap and analyze from available data only
"""


def format_fighter_block(f: dict) -> str:
    r = f["record"]
    s = f["striking"]
    g = f["grappling"]
    wm = f["win_methods"]
    wm_note = wm.get("note", "")
    is_debut = f.get("ufc_debut", False)
    debut_source = f.get("debut_source", "Tapology")

    history_lines = []
    for fight in f["fight_history"]:
        line = f"  {fight['result']} vs {fight['opponent']} -- {fight['method']}"
        if fight.get("promotion"):
            line += f" [{fight['promotion']}]"
        if fight.get("round") and fight["round"] != "N/A":
            line += f", R{fight['round']}"
        if fight.get("time") and fight["time"] != "N/A":
            line += f" ({fight['time']})"
        history_lines.append(line)

    history_text = (
        "\n".join(history_lines) if history_lines else "  (No fight history parsed)"
    )

    debut_header = ""
    stats_note = ""
    if is_debut:
        debut_header = f"  *** UFC DEBUT -- stats sourced from {debut_source} (pre-UFC career) ***\n"
        stats_note = (
            "\nNOTE: UFC per-minute striking/grappling averages are not available for this fighter "
            "as they have no UFC fights. Analyze their style based on fight history and win methods only."
        )

    return f"""=== {f['name'].upper()} ===
{debut_header}Record: {r['wins']}-{r['losses']}-{r['draws']}
Height: {f['height']} | Weight: {f['weight']} | Reach: {f['reach']} | Stance: {f['stance']}

Striking (career averages -- UFC only):
  {s['slpm']} sig. strikes landed/min | {s['sapm']} absorbed/min
  {s['str_acc']} striking accuracy | {s['str_def']} strike defense

Grappling (career averages -- UFC only):
  {g['td_avg']} takedowns/15min | {g['td_acc']} TD accuracy | {g['td_def']} TD defense
  {g['sub_avg']} submission attempts/15min

Win methods {wm_note}: {wm['ko']} KO/TKO | {wm['sub']} Submissions | {wm['dec']} Decisions

Recent fight history (most recent first):
{history_text}{stats_note}"""


def build_prompt(f1: dict, f2: dict) -> str:
    return f"""{format_fighter_block(f1)}

{format_fighter_block(f2)}

---

Produce the following analysis in this EXACT format, including the HTML comment markers exactly as shown:

<!--F1_PROFILE-->
## {f1['name']} -- Style & Profile
[Write 4-6 concise bullet points. Each bullet = one key insight: fighting style, best weapon, stat-backed tendency, behavior under pressure, or notable pattern from fight history. Be specific, cite numbers. No filler.]
<!--END-->

<!--F2_PROFILE-->
## {f2['name']} -- Style & Profile
[Same structure as above -- 4-6 concise bullet points.]
<!--END-->

<!--HEAD2HEAD-->
## Head-to-Head: Strengths & Weaknesses
[2-3 paragraphs analyzing how these styles interact. Where does each fighter have the edge? What are the critical exchanges that will decide this fight? Be specific about which stats matter most in this matchup.]
<!--END-->

<!--ENDINGS-->
## 3-5 Most Likely Fight Endings (Ranked by Probability)

Generate between 3 and 5 outcomes. Use 3 when the matchup has a clear stylistic favorite and limited realistic scenarios. Use 4 or 5 when there are multiple genuinely plausible paths to victory for either fighter.

**#1 -- [Specific description, e.g., "Jon Jones wins by TKO, Round 3"]**
Probability: [X]%
Why: [2-3 sentences of specific reasoning]

**#2 -- [Specific description]**
Probability: [X]%
Why: [2-3 sentences of specific reasoning]

**#3 -- [Specific description]**
Probability: [X]%
Why: [2-3 sentences of specific reasoning]

[Add #4 and #5 only if the matchup genuinely warrants additional scenarios]
<!--END-->

<!--BETTING-->
Include the full betting recommendation as defined in the BETTING RECOMMENDATION RULES in the system prompt. Use the exact structure specified there.
<!--END-->"""


def parse_analysis_sections(text: str) -> dict:
    """Extract sections between <!--TAG--> and <!--END--> markers."""
    sections = {}
    pattern = r"<!--(\w+)-->(.*?)<!--END-->"
    for match in re.finditer(pattern, text, re.DOTALL):
        key = match.group(1).lower()
        sections[key] = match.group(2).strip()
    return sections


def get_analysis(f1: dict, f2: dict) -> str:
    """Returns Claude's full analysis as a single string."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    prompt = build_prompt(f1, f2)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _books_for_table(annotated: list[dict]) -> list[dict]:
    """Remap annotated books to match the component's expected keys."""
    result = []
    for b in annotated:
        result.append({
            "book": b.get("name", b.get("book", "Unknown")),
            "f1_odds": b["f1_odds"],
            "f2_odds": b["f2_odds"],
            "f1_best": b.get("f1_best", False),
            "f2_best": b.get("f2_best", False),
        })
    return result


# -- Fighter stat card ---------------------------------------------------------

def show_fighter_card(
    f: dict,
    image_url: str | None = None,
    profile_text: str | None = None,
):
    r = f["record"]
    s = f["striking"]
    g = f["grappling"]
    is_debut = f.get("ufc_debut", False)
    debut_source = f.get("debut_source", "Tapology")

    if image_url:
        st.image(image_url, width=200)

    if is_debut:
        st.markdown(
            '<span class="debut-badge">UFC Debut</span>',
            unsafe_allow_html=True,
        )

    st.markdown(f"### {f['name']}")

    if is_debut:
        st.caption(f"No UFC record -- stats sourced from {debut_source} (pre-UFC career)")

    st.markdown(
        f"**{r['wins']}-{r['losses']}-{r['draws']}** \u00b7 "
        f"{f['height']} \u00b7 {f['weight']} \u00b7 Reach: {f['reach']} \u00b7 {f['stance']}"
    )

    c1, c2 = st.columns(2)
    if is_debut:
        with c1:
            st.markdown("**Striking**")
            st.markdown("*N/A -- no UFC fights*")
        with c2:
            st.markdown("**Grappling**")
            st.markdown("*N/A -- no UFC fights*")
    else:
        with c1:
            st.markdown("**Striking**")
            st.markdown(
                f"- Landed/min: **{s['slpm']}**\n"
                f"- Accuracy: **{s['str_acc']}**\n"
                f"- Absorbed/min: **{s['sapm']}**\n"
                f"- Defense: **{s['str_def']}**"
            )
        with c2:
            st.markdown("**Grappling**")
            st.markdown(
                f"- TD avg: **{g['td_avg']}**/15min\n"
                f"- TD accuracy: **{g['td_acc']}**\n"
                f"- TD defense: **{g['td_def']}**\n"
                f"- Sub avg: **{g['sub_avg']}**/15min"
            )

    with st.expander("Recent fight history"):
        for fight in f["fight_history"]:
            emoji = (
                "W" if fight["result"] == "WIN"
                else ("L" if fight["result"] == "LOSS" else "D")
            )
            round_time = ""
            if fight.get("round") and fight["round"] != "N/A":
                round_time = f" R{fight['round']}"
                if fight.get("time") and fight["time"] != "N/A":
                    round_time += f" ({fight['time']})"
            yt_url = yt_fight_url(f["name"], fight["opponent"])
            st.markdown(
                f"**{emoji}** vs **{fight['opponent']}** -- {fight['method']}{round_time} "
                f"[Watch]({yt_url})"
            )

    if profile_text:
        analysis_section(f"Style Profile: {f['name']}", profile_text, icon="\u26a1")


# -- Fight preview panel -------------------------------------------------------

def show_fight_preview(fight: dict, fight_index: int):
    f1_name = fight["fighter1"]
    f2_name = fight["fighter2"]

    # Fetch images
    f1_img = get_fighter_image(f1_name)
    f2_img = get_fighter_image(f2_name)

    # Fetch odds
    odds_data = None
    f1_odds = None
    f2_odds = None
    try:
        odds_data = find_fight_odds(f1_name, f2_name)
        if odds_data:
            f1_odds = odds_data["best_f1"]["odds"]
            f2_odds = odds_data["best_f2"]["odds"]
    except Exception:
        pass

    # VS header
    fighter_vs_header(f1_name, f2_name, f1_img, f2_img, f1_odds, f2_odds)

    # Odds table
    if odds_data and odds_data.get("books"):
        annotated = annotate_odds_table(odds_data["books"], f1_name, f2_name)
        odds_comparison_table(_books_for_table(annotated))

    # Stake input
    st.number_input(
        "Total stake ($)",
        min_value=10.0,
        max_value=10000.0,
        value=100.0,
        step=10.0,
        key=f"stake_{fight_index}",
    )

    # Analysis button
    if st.button(
        "Full Analysis",
        key=f"analyze_{fight_index}",
        use_container_width=True,
        type="primary",
    ):
        st.session_state.f1 = f1_name
        st.session_state.f2 = f2_name
        st.session_state.total_stake = st.session_state.get(
            f"stake_{fight_index}", 100.0
        )
        st.session_state.do_analysis = True


# -- Run analysis pipeline ----------------------------------------------------

def run_analysis_pipeline(f1_name: str, f2_name: str, total_stake: float):
    """Full analysis pipeline: scrape fighters, fetch odds, hedge calc, Claude AI."""

    if not os.environ.get("FIRECRAWL_API_KEY"):
        st.error("FIRECRAWL_API_KEY not configured. Check your Streamlit secrets.")
        st.stop()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY not configured. Check your Streamlit secrets.")
        st.stop()

    f1_data = None
    f2_data = None

    # -- 1. Scrape fighters (with debut fallback) -----------------------------
    with st.status("Fetching fighter data...", expanded=True) as status:
        try:
            st.write(f"Looking up **{f1_name}** on ufcstats.com...")
            try:
                f1_data = scrape_fighter(f1_name)
                st.write(
                    f"Found {f1_data['name']} "
                    f"({f1_data['record']['wins']}-{f1_data['record']['losses']}-{f1_data['record']['draws']})"
                )
            except (ValueError, SystemExit):
                st.write("Not on ufcstats.com -- trying Tapology (UFC debut?)...")
                f1_data = scrape_debut_fighter(f1_name)
                st.write(
                    f"**UFC Debut:** {f1_data['name']} "
                    f"({f1_data['record']['wins']}-{f1_data['record']['losses']}-{f1_data['record']['draws']}) "
                    f"-- stats from {f1_data['debut_source']}"
                )

            st.write(f"Looking up **{f2_name}** on ufcstats.com...")
            try:
                f2_data = scrape_fighter(f2_name)
                st.write(
                    f"Found {f2_data['name']} "
                    f"({f2_data['record']['wins']}-{f2_data['record']['losses']}-{f2_data['record']['draws']})"
                )
            except (ValueError, SystemExit):
                st.write("Not on ufcstats.com -- trying Tapology (UFC debut?)...")
                f2_data = scrape_debut_fighter(f2_name)
                st.write(
                    f"**UFC Debut:** {f2_data['name']} "
                    f"({f2_data['record']['wins']}-{f2_data['record']['losses']}-{f2_data['record']['draws']}) "
                    f"-- stats from {f2_data['debut_source']}"
                )

            st.write("Fetching fighter images...")
            f1_img = get_fighter_image(f1_data["name"])
            f2_img = get_fighter_image(f2_data["name"])

            status.update(label="Data fetched!", state="complete")
        except (ValueError, SystemExit):
            status.update(label="Fighter not found", state="error")
            st.error(
                "Could not find one of the fighters on ufcstats.com or Tapology. "
                "Check the spelling and try the full name (e.g., 'Jon Jones' not 'Jones')."
            )
            st.stop()
        except Exception as e:
            status.update(label="Error fetching data", state="error")
            st.error(f"Error: {e}")
            st.stop()

    # -- 2. Fetch odds ---------------------------------------------------------
    odds_data = None
    hedge_summary = None
    f1_odds = None
    f2_odds = None

    try:
        odds_data = find_fight_odds(f1_data["name"], f2_data["name"])
        if odds_data:
            f1_odds = odds_data["best_f1"]["odds"]
            f2_odds = odds_data["best_f2"]["odds"]
            hedge_summary = summarize_hedge(
                f1_data["name"], f2_data["name"], odds_data, total_stake
            )
    except Exception:
        pass

    # -- 3. Generate Claude analysis -------------------------------------------
    analysis_sections = {}
    with st.spinner("Generating AI analysis..."):
        try:
            raw_analysis = get_analysis(f1_data, f2_data)
            analysis_sections = parse_analysis_sections(raw_analysis)
        except anthropic.AuthenticationError:
            st.error("Invalid Anthropic API key. Check your Streamlit secrets.")
            st.stop()
        except Exception as e:
            st.error(f"Analysis error: {e}")
            st.stop()

    # -- 4. Render everything --------------------------------------------------
    st.divider()

    # VS header with odds
    fighter_vs_header(
        f1_data["name"],
        f2_data["name"],
        f1_img,
        f2_img,
        f1_odds,
        f2_odds,
    )

    # Odds table
    if odds_data and odds_data.get("books"):
        annotated = annotate_odds_table(
            odds_data["books"], f1_data["name"], f2_data["name"]
        )
        odds_comparison_table(_books_for_table(annotated))

    # Arb / no-arb banner + hedge card
    if hedge_summary:
        if hedge_summary["arb_exists"]:
            arb_banner(
                hedge_summary["roi_pct"],
                hedge_summary["guaranteed_profit"],
                hedge_summary["total_stake"],
            )
            hedge_result_card(
                f1_name=hedge_summary["f1_name"],
                f2_name=hedge_summary["f2_name"],
                f1_stake=hedge_summary["f1_stake"],
                f2_stake=hedge_summary["f2_stake"],
                f1_book=hedge_summary["f1_book"],
                f2_book=hedge_summary["f2_book"],
                f1_odds=hedge_summary["f1_odds"],
                f2_odds=hedge_summary["f2_odds"],
                guaranteed_profit=hedge_summary["guaranteed_profit"],
                roi_pct=hedge_summary["roi_pct"],
            )
        else:
            if odds_data:
                no_arb_banner(
                    odds_data["best_f1"]["book"],
                    odds_data["best_f1"]["odds"],
                    odds_data["best_f2"]["book"],
                    odds_data["best_f2"]["odds"],
                )
    elif not odds_data:
        # Graceful degradation: no odds available
        st.info(
            "Live odds not yet available for this fight. "
            "Enter odds manually to use the hedge calculator."
        )
        mc1, mc2 = st.columns(2)
        with mc1:
            f1_manual = st.number_input(
                f"{f1_data['name']} odds (American)",
                value=0,
                step=5,
                key="manual_f1_odds",
            )
        with mc2:
            f2_manual = st.number_input(
                f"{f2_data['name']} odds (American)",
                value=0,
                step=5,
                key="manual_f2_odds",
            )
        if f1_manual != 0 and f2_manual != 0:
            manual_stakes = calculate_stakes(f1_manual, f2_manual, total_stake)
            if manual_stakes["arb_exists"]:
                arb_banner(
                    manual_stakes["roi_pct"],
                    manual_stakes["guaranteed_profit"],
                    manual_stakes["total_stake"],
                )
                hedge_result_card(
                    f1_name=f1_data["name"],
                    f2_name=f2_data["name"],
                    f1_stake=manual_stakes["f1_stake"],
                    f2_stake=manual_stakes["f2_stake"],
                    f1_book="Manual",
                    f2_book="Manual",
                    f1_odds=f1_manual,
                    f2_odds=f2_manual,
                    guaranteed_profit=manual_stakes["guaranteed_profit"],
                    roi_pct=manual_stakes["roi_pct"],
                )
            else:
                no_arb_banner("Manual", f1_manual, "Manual", f2_manual)

    # Fighter cards side by side
    col1, col2 = st.columns(2)
    with col1:
        show_fighter_card(
            f1_data,
            image_url=f1_img,
            profile_text=analysis_sections.get("f1_profile"),
        )
    with col2:
        show_fighter_card(
            f2_data,
            image_url=f2_img,
            profile_text=analysis_sections.get("f2_profile"),
        )

    # Head-to-head
    if analysis_sections.get("head2head"):
        analysis_section(
            "Head-to-Head: Strengths & Weaknesses",
            analysis_sections["head2head"],
            icon="\U0001f94a",
        )

    # Fight endings
    if analysis_sections.get("endings"):
        analysis_section(
            "Most Likely Fight Endings",
            analysis_sections["endings"],
            icon="\U0001f3af",
        )

    # Betting recommendation
    if analysis_sections.get("betting"):
        betting_rec_section(analysis_sections["betting"])


# -- Tabs ----------------------------------------------------------------------

tab1, tab2 = st.tabs(["\U0001f5d3\ufe0f Fight Card", "\U0001f50d Manual Search"])

with tab1:
    if not os.environ.get("FIRECRAWL_API_KEY"):
        st.warning("FIRECRAWL_API_KEY not configured -- cannot load upcoming card.")
    else:
        with st.spinner("Loading upcoming fight card..."):
            try:
                card = load_card_for_week(get_week_key())
            except Exception as e:
                st.error(f"Could not load upcoming card: {e}")
                card = None

        if card:
            event_banner(card["event_name"], card["date"], card["location"])
            st.caption("*Card refreshes automatically each week*")
            st.divider()

            if not card["fights"]:
                st.info(
                    "No fights found on the card yet. Check back closer to the event."
                )
            else:
                for i, fight in enumerate(card["fights"]):
                    wc = fight["weight_class"] if fight["weight_class"] != "N/A" else ""
                    label = f"**{fight['fighter1']}** vs **{fight['fighter2']}**"
                    if wc:
                        label += f"  \u00b7  *{wc}*"
                    with st.expander(label):
                        show_fight_preview(fight, i)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        manual_f1 = st.text_input("Fighter 1", placeholder="e.g. Jon Jones")
    with col2:
        manual_f2 = st.text_input("Fighter 2", placeholder="e.g. Stipe Miocic")

    manual_stake = st.number_input(
        "Total stake ($)",
        min_value=10.0,
        max_value=10000.0,
        value=100.0,
        step=10.0,
        key="manual_stake",
    )

    if st.button("Analyze Matchup", type="primary", use_container_width=True):
        if not manual_f1.strip() or not manual_f2.strip():
            st.error("Please enter both fighter names.")
        else:
            st.session_state.f1 = manual_f1.strip()
            st.session_state.f2 = manual_f2.strip()
            st.session_state.total_stake = manual_stake
            st.session_state.do_analysis = True

# -- Analysis trigger ----------------------------------------------------------

if st.session_state.do_analysis:
    st.session_state.do_analysis = False
    f1_name = st.session_state.f1
    f2_name = st.session_state.f2
    total_stake = st.session_state.total_stake

    if not f1_name or not f2_name:
        st.error("Fighter names missing. Please select or enter both fighters.")
        st.stop()

    run_analysis_pipeline(f1_name, f2_name, total_stake)
