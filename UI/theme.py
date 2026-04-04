"""UFC 5 Design System — Premium Dark Sportsbook Theme.

Call get_css() once at app start and inject via:
    st.markdown(get_css(), unsafe_allow_html=True)
"""


def get_css() -> str:
    """Return the full CSS stylesheet for the UFC 5 sportsbook UI."""
    return """<style>
/* ===== GOOGLE FONT ===== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

/* ===== BASE LAYOUT ===== */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #0a0a0b !important;
    font-family: 'Inter', sans-serif !important;
    color: #f0f0f0;
}

[data-testid="stHeader"] {
    background-color: #0a0a0b !important;
}

.main .block-container {
    max-width: 1200px;
    padding: 2rem;
}

/* ===== TYPOGRAPHY ===== */
h1 {
    font-size: 2.6rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px !important;
    color: #f0f0f0 !important;
}

h2, h3, h4 {
    color: #f0f0f0 !important;
    font-weight: 700 !important;
}

p, li {
    color: #d0d0d8;
    line-height: 1.7;
}

strong {
    color: #f0f0f0;
}

hr {
    border-color: #d4af37 !important;
    opacity: 0.3;
}

/* ===== TABS ===== */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #13151a;
    border-radius: 10px;
    border: 1px solid #1e2028;
    gap: 0;
    padding: 4px;
}

[data-testid="stTabs"] [data-baseweb="tab"] {
    color: #8a8f9e !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    border: none !important;
    background: transparent !important;
    padding: 8px 20px;
}

[data-testid="stTabs"] [aria-selected="true"] {
    color: #0a0a0b !important;
    background: #d4af37 !important;
}

[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    display: none;
}

/* ===== BUTTONS ===== */
[data-testid="stButton"] > button[kind="primary"],
[data-testid="stButton"] > button {
    background-color: #C8102E !important;
    color: white !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    border: none !important;
    transition: background-color 0.2s ease;
}

[data-testid="stButton"] > button:hover {
    background-color: #a00d25 !important;
}

[data-testid="stButton"] > button[kind="secondary"] {
    background-color: #13151a !important;
    border: 1px solid #1e2028 !important;
    color: white !important;
    border-radius: 8px !important;
}

/* ===== EXPANDERS ===== */
[data-testid="stExpander"] {
    background-color: #13151a !important;
    border: 1px solid #1e2028 !important;
    border-radius: 10px !important;
}

[data-testid="stExpander"] summary {
    color: white !important;
    font-weight: 600 !important;
}

[data-testid="stExpander"] summary:hover {
    color: #d4af37 !important;
}

/* ===== TEXT INPUTS ===== */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] [data-baseweb="select"],
[data-testid="stTextArea"] textarea {
    background-color: #13151a !important;
    border: 1px solid #1e2028 !important;
    color: white !important;
    border-radius: 8px !important;
}

[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #d4af37 !important;
    box-shadow: 0 0 0 2px rgba(212,175,55,0.2) !important;
}

[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stTextArea"] label {
    color: #8a8f9e !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* ===== FIGHT CARD BANNER ===== */
.fight-card-banner {
    background: linear-gradient(135deg, #13151a 0%, #1a1c23 100%);
    border-left: 4px solid #d4af37;
    border-radius: 12px;
    padding: 20px 24px;
}

/* ===== FIGHTER VS BLOCK ===== */
.fighter-vs-block {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 16px;
    align-items: center;
}

.fighter-slot {
    background: #13151a;
    border: 1px solid #1e2028;
    border-radius: 12px;
    padding: 20px;
    transition: box-shadow 0.2s ease;
    text-align: center;
}

.fighter-slot:hover {
    box-shadow: 0 0 20px rgba(212,175,55,0.15);
}

.vs-divider {
    color: #d4af37;
    font-size: 1.4rem;
    font-weight: 800;
    text-align: center;
}

/* ===== MONEYLINE PILL ===== */
.moneyline-pill {
    display: inline-block;
    background: #1e2028;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 800;
    font-size: 1.1rem;
    letter-spacing: 0.5px;
}

.moneyline-pill.positive {
    color: #00c853;
}

.moneyline-pill.negative {
    color: #ff6b6b;
}

.moneyline-pill.neutral {
    color: #d4af37;
}

/* ===== ODDS TABLE ===== */
.odds-table {
    width: 100%;
    border-collapse: collapse;
    background: #13151a;
    border-radius: 10px;
    overflow: hidden;
}

.odds-table th {
    background: #1e2028;
    color: #8a8f9e;
    text-transform: uppercase;
    font-size: 0.78rem;
    letter-spacing: 0.8px;
    padding: 12px 16px;
    text-align: left;
}

.odds-table td {
    padding: 12px 16px;
    border-bottom: 1px solid #1e2028;
    color: #f0f0f0;
}

.odds-table tr:last-child td {
    border-bottom: none;
}

.odds-table tr:hover td {
    background: rgba(212,175,55,0.05);
}

.odds-table .best-line {
    color: #d4af37;
    font-weight: 700;
}

/* ===== ARB BANNER ===== */
.arb-banner {
    background: linear-gradient(135deg, rgba(0,200,83,0.15), rgba(0,200,83,0.05));
    border: 1px solid #00c853;
    border-radius: 12px;
    padding: 18px 22px;
    color: #00c853;
}

/* ===== NO-ARB BANNER ===== */
.no-arb-banner {
    background: rgba(255,23,68,0.08);
    border: 1px solid rgba(255,23,68,0.3);
    border-radius: 12px;
    padding: 14px 18px;
    color: #ff6b6b;
}

/* ===== HEDGE RESULT CARD ===== */
.hedge-result-card {
    background: #13151a;
    border: 1px solid #1e2028;
    border-radius: 12px;
    padding: 22px;
}

.hedge-result-card .bet-row {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #1e2028;
    align-items: center;
}

.hedge-result-card .bet-row:last-of-type {
    border-bottom: none;
}

.hedge-result-card .bet-book {
    color: #8a8f9e;
    font-size: 0.9rem;
}

.hedge-result-card .bet-amount {
    color: #d4af37;
    font-weight: 700;
    font-size: 1.1rem;
}

.hedge-result-card .profit-line {
    color: #00c853;
    font-weight: 800;
    font-size: 1.2rem;
    padding-top: 12px;
}

/* ===== ANALYSIS BLOCK ===== */
.analysis-block {
    background: #13151a;
    border: 1px solid #1e2028;
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 16px;
}

/* ===== SECTION LABEL ===== */
.section-label {
    border-left: 4px solid #d4af37;
    padding-left: 12px;
    margin: 28px 0 14px 0;
    color: #f0f0f0;
    font-weight: 700;
    font-size: 1.1rem;
}

/* ===== CONFIDENCE CHIP ===== */
.confidence-chip {
    display: inline-block;
    background: rgba(212,175,55,0.15);
    border: 1px solid rgba(212,175,55,0.4);
    color: #d4af37;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.82rem;
    font-weight: 700;
}

/* ===== BETTING REC BLOCK ===== */
.betting-rec-block {
    background: linear-gradient(135deg, rgba(212,175,55,0.08), rgba(212,175,55,0.03));
    border: 1px solid rgba(212,175,55,0.25);
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 16px;
}

.betting-rec-block .rec-header {
    color: #d4af37;
    font-weight: 800;
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 12px;
}

/* ===== DEBUT BADGE ===== */
.debut-badge {
    background: linear-gradient(135deg, #d4af37, #b8890f);
    color: #000;
    font-weight: 800;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 0.72rem;
    display: inline-block;
}

/* ===== ODDS FLASH ANIMATION ===== */
@keyframes oddsFlash {
    0% { background-color: rgba(212,175,55,0.3); }
    100% { background-color: transparent; }
}

.odds-updated {
    animation: oddsFlash 0.8s ease-out;
}

/* ===== SCROLLBAR ===== */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: #0a0a0b;
}

::-webkit-scrollbar-thumb {
    background: #1e2028;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #2a2d38;
}
</style>"""
