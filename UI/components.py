"""UFC 5 UI Components — Reusable HTML components for the sportsbook interface.

All functions render HTML via st.markdown(..., unsafe_allow_html=True).
Requires theme.get_css() to be injected first for styling.
"""

import streamlit as st


def _format_odds(odds: int | None) -> str:
    """Format American odds with +/- prefix."""
    if odds is None:
        return "N/A"
    return f"+{odds}" if odds > 0 else str(odds)


def _odds_class(odds: int | None) -> str:
    """Return moneyline-pill modifier class based on odds sign."""
    if odds is None:
        return "neutral"
    return "positive" if odds > 0 else "negative"


def _initials_avatar(name: str) -> str:
    """Return HTML for an initials-based avatar circle."""
    initial = name.strip()[0].upper() if name.strip() else "?"
    return (
        f'<div style="width:160px;height:160px;border-radius:50%;'
        f'background:#1e2028;display:flex;align-items:center;'
        f'justify-content:center;margin:0 auto 12px auto;'
        f'font-size:3rem;font-weight:800;color:#d4af37;">'
        f'{initial}</div>'
    )


def fighter_vs_header(
    f1_name: str,
    f2_name: str,
    f1_img_url: str | None,
    f2_img_url: str | None,
    f1_odds: int | None,
    f2_odds: int | None,
) -> None:
    """Render the fighter VS block with photos and moneyline odds."""
    f1_img = (
        f'<img src="{f1_img_url}" style="width:160px;height:160px;'
        f'object-fit:cover;border-radius:50%;margin-bottom:12px;" />'
        if f1_img_url
        else _initials_avatar(f1_name)
    )
    f2_img = (
        f'<img src="{f2_img_url}" style="width:160px;height:160px;'
        f'object-fit:cover;border-radius:50%;margin-bottom:12px;" />'
        if f2_img_url
        else _initials_avatar(f2_name)
    )

    html = f"""
    <div class="fighter-vs-block">
        <div class="fighter-slot">
            {f1_img}
            <div style="font-size:1.2rem;font-weight:700;color:#f0f0f0;margin-bottom:8px;">
                {f1_name}
            </div>
            <span class="moneyline-pill {_odds_class(f1_odds)}">
                {_format_odds(f1_odds)}
            </span>
        </div>
        <div class="vs-divider">VS</div>
        <div class="fighter-slot">
            {f2_img}
            <div style="font-size:1.2rem;font-weight:700;color:#f0f0f0;margin-bottom:8px;">
                {f2_name}
            </div>
            <span class="moneyline-pill {_odds_class(f2_odds)}">
                {_format_odds(f2_odds)}
            </span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def odds_comparison_table(odds_list: list[dict]) -> None:
    """Render multi-book odds comparison table.

    Args:
        odds_list: List of dicts with keys:
            book (str), f1_odds (int), f2_odds (int),
            f1_best (bool), f2_best (bool)
    """
    if not odds_list:
        return

    rows = ""
    for entry in odds_list:
        book = entry["book"]
        f1 = entry["f1_odds"]
        f2 = entry["f2_odds"]
        f1_cls = ' class="best-line"' if entry.get("f1_best") else ""
        f2_cls = ' class="best-line"' if entry.get("f2_best") else ""
        f1_prefix = '<span style="margin-right:4px;">&#9733;</span>' if entry.get("f1_best") else ""
        f2_prefix = '<span style="margin-right:4px;">&#9733;</span>' if entry.get("f2_best") else ""

        rows += f"""
        <tr>
            <td style="font-weight:600;">{book}</td>
            <td{f1_cls}>{f1_prefix}{_format_odds(f1)}</td>
            <td{f2_cls}>{f2_prefix}{_format_odds(f2)}</td>
        </tr>"""

    html = f"""
    <table class="odds-table">
        <thead>
            <tr>
                <th>Sportsbook</th>
                <th>Fighter 1</th>
                <th>Fighter 2</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    """
    st.markdown(html, unsafe_allow_html=True)


def arb_banner(roi_pct: float, guaranteed_profit: float, total_stake: float) -> None:
    """Render green ARB FOUND banner with ROI and profit."""
    html = f"""
    <div class="arb-banner">
        <div style="font-size:1.3rem;font-weight:800;margin-bottom:8px;">
            &#9989; ARB FOUND
        </div>
        <div style="display:flex;gap:24px;flex-wrap:wrap;">
            <div>
                <span style="color:#8a8f9e;font-size:0.82rem;text-transform:uppercase;
                    letter-spacing:0.6px;">ROI</span><br/>
                <span style="font-weight:800;font-size:1.2rem;">{roi_pct:.2f}%</span>
            </div>
            <div>
                <span style="color:#8a8f9e;font-size:0.82rem;text-transform:uppercase;
                    letter-spacing:0.6px;">Guaranteed Profit</span><br/>
                <span style="font-weight:800;font-size:1.2rem;">${guaranteed_profit:,.2f}</span>
            </div>
            <div>
                <span style="color:#8a8f9e;font-size:0.82rem;text-transform:uppercase;
                    letter-spacing:0.6px;">Total Stake</span><br/>
                <span style="font-weight:800;font-size:1.2rem;">${total_stake:,.2f}</span>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def no_arb_banner(
    best_f1_book: str,
    best_f1_odds: int,
    best_f2_book: str,
    best_f2_odds: int,
) -> None:
    """Render no-arb banner with best available lines."""
    html = f"""
    <div class="no-arb-banner">
        <div style="font-weight:700;margin-bottom:8px;">
            &#10060; No guaranteed arb
        </div>
        <div style="color:#d0d0d8;font-size:0.92rem;">
            Best available lines:
            <strong style="color:#f0f0f0;">{best_f1_book}</strong>
            <span class="moneyline-pill {_odds_class(best_f1_odds)}" style="font-size:0.9rem;padding:3px 10px;">
                {_format_odds(best_f1_odds)}
            </span>
            &nbsp;|&nbsp;
            <strong style="color:#f0f0f0;">{best_f2_book}</strong>
            <span class="moneyline-pill {_odds_class(best_f2_odds)}" style="font-size:0.9rem;padding:3px 10px;">
                {_format_odds(best_f2_odds)}
            </span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def hedge_result_card(
    f1_name: str,
    f2_name: str,
    f1_stake: float,
    f2_stake: float,
    f1_book: str,
    f2_book: str,
    f1_odds: int,
    f2_odds: int,
    guaranteed_profit: float,
    roi_pct: float,
) -> None:
    """Render the hedge betting instruction card."""
    html = f"""
    <div class="hedge-result-card">
        <div style="font-weight:700;font-size:1.1rem;color:#f0f0f0;margin-bottom:14px;">
            Hedge Betting Instructions
        </div>
        <div class="bet-row">
            <div>
                <span style="color:#f0f0f0;font-weight:600;">{f1_name}</span>
                <span class="bet-book">&nbsp;on {f1_book} ({_format_odds(f1_odds)})</span>
            </div>
            <div class="bet-amount">${f1_stake:,.2f}</div>
        </div>
        <div class="bet-row">
            <div>
                <span style="color:#f0f0f0;font-weight:600;">{f2_name}</span>
                <span class="bet-book">&nbsp;on {f2_book} ({_format_odds(f2_odds)})</span>
            </div>
            <div class="bet-amount">${f2_stake:,.2f}</div>
        </div>
        <div class="profit-line">
            Guaranteed Profit: ${guaranteed_profit:,.2f} &nbsp;
            <span style="font-size:0.9rem;color:#8a8f9e;">(ROI: {roi_pct:.2f}%)</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def analysis_section(title: str, content: str, icon: str = "\U0001f94a") -> None:
    """Render an analysis content block with title."""
    html = f"""
    <div class="section-label">{icon} {title}</div>
    <div class="analysis-block">
        {content}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def betting_rec_section(content: str) -> None:
    """Render the gold-accented betting recommendation block."""
    html = f"""
    <div class="betting-rec-block">
        <div class="rec-header">\U0001f4b0 Betting Recommendation</div>
        <div style="color:#d0d0d8;line-height:1.7;">{content}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def event_banner(event_name: str, date: str, location: str) -> None:
    """Render the event header banner."""
    html = f"""
    <div class="fight-card-banner">
        <div style="font-size:1.6rem;font-weight:800;color:#f0f0f0;margin-bottom:6px;">
            {event_name}
        </div>
        <div style="font-size:0.92rem;color:#d4af37;font-weight:600;">
            {date} &nbsp;&bull;&nbsp; {location}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
