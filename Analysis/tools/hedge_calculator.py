"""
hedge_calculator.py — Arbitrage and hedge betting math for UFC.

All odds are in American format (e.g., +150, -175).
"""


def american_to_decimal(odds: int) -> float:
    """Convert American odds to decimal (European) format.
    +150 -> 2.50, -175 -> 1.571
    """
    if odds > 0:
        return (odds / 100) + 1
    else:
        return (100 / abs(odds)) + 1


def american_to_implied(odds: int) -> float:
    """Convert American odds to implied probability (0-1).
    +150 -> 0.4, -175 -> 0.6364
    """
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def decimal_to_american(decimal_odds: float) -> int:
    """Convert decimal odds back to American format."""
    if decimal_odds >= 2.0:
        return round((decimal_odds - 1) * 100)
    else:
        return round(-100 / (decimal_odds - 1))


def find_arb_pct(f1_odds: int, f2_odds: int) -> float:
    """
    Returns the arbitrage percentage.
    Positive = guaranteed profit exists.
    Calculated as: (1 - sum_of_implied_probs) * 100
    Example: f1 +150, f2 +130 -> implied 0.40 + 0.4348 = 0.8348 -> arb = 16.52%
    """
    combined = american_to_implied(f1_odds) + american_to_implied(f2_odds)
    return (1 - combined) * 100


def calculate_stakes(f1_odds: int, f2_odds: int, total_stake: float) -> dict:
    """
    Calculate optimal stake split for a guaranteed-profit hedge.

    Uses equal-profit formula so that net profit is the same regardless
    of which fighter wins.

    Returns:
    {
        "f1_stake": float,
        "f2_stake": float,
        "total_stake": float,
        "guaranteed_profit": float,
        "roi_pct": float,
        "arb_exists": bool,
    }
    """
    dec1 = american_to_decimal(f1_odds)
    dec2 = american_to_decimal(f2_odds)

    # For equal profit on both outcomes:
    # f1_stake * dec1 = f2_stake * dec2  (equal payout)
    # f1_stake + f2_stake = total_stake
    #
    # Solving: f1_stake = total_stake * dec2 / (dec1 + dec2)
    #          f2_stake = total_stake * dec1 / (dec1 + dec2)
    f1_stake = total_stake * dec2 / (dec1 + dec2)
    f2_stake = total_stake * dec1 / (dec1 + dec2)

    # Payout is the same regardless of winner
    payout = f1_stake * dec1  # == f2_stake * dec2
    guaranteed_profit = payout - total_stake
    roi_pct = (guaranteed_profit / total_stake) * 100

    return {
        "f1_stake": round(f1_stake, 2),
        "f2_stake": round(f2_stake, 2),
        "total_stake": round(total_stake, 2),
        "guaranteed_profit": round(guaranteed_profit, 2),
        "roi_pct": round(roi_pct, 2),
        "arb_exists": roi_pct > 0,
    }


def best_value_line(odds_list: list[dict], fighter_key: str) -> dict:
    """
    Given a list of {"book": str, "f1_odds": int, "f2_odds": int} dicts,
    returns the dict with the best (highest) American odds for fighter_key
    ("f1_odds" or "f2_odds").
    """
    return max(odds_list, key=lambda x: x[fighter_key])


def annotate_odds_table(books: list[dict], f1_name: str, f2_name: str) -> list[dict]:
    """
    Takes raw books list and adds f1_best/f2_best boolean flags.
    Returns enhanced list suitable for the UI odds_comparison_table() component.
    """
    if not books:
        return []

    best_f1_odds = max(b["f1_odds"] for b in books)
    best_f2_odds = max(b["f2_odds"] for b in books)

    annotated = []
    for book in books:
        annotated.append({
            **book,
            "f1_name": f1_name,
            "f2_name": f2_name,
            "f1_best": book["f1_odds"] == best_f1_odds,
            "f2_best": book["f2_odds"] == best_f2_odds,
        })
    return annotated


def summarize_hedge(
    f1_name: str,
    f2_name: str,
    odds_data: dict,
    total_stake: float = 100.0,
) -> dict:
    """
    Full summary given find_fight_odds() output.
    Uses best available line for each fighter (cross-book arb).

    Returns:
    {
        "arb_exists": bool,
        "roi_pct": float,
        "guaranteed_profit": float,
        "f1_name": str,
        "f2_name": str,
        "f1_stake": float,
        "f2_stake": float,
        "f1_book": str,
        "f2_book": str,
        "f1_odds": int,
        "f2_odds": int,
        "total_stake": float,
        "annotated_books": list[dict],
    }
    """
    f1_odds = odds_data["best_f1"]["odds"]
    f2_odds = odds_data["best_f2"]["odds"]
    f1_book = odds_data["best_f1"]["book"]
    f2_book = odds_data["best_f2"]["book"]

    stakes = calculate_stakes(f1_odds, f2_odds, total_stake)
    annotated = annotate_odds_table(
        odds_data["books"],
        odds_data.get("fighter1", f1_name),
        odds_data.get("fighter2", f2_name),
    )

    return {
        "arb_exists": stakes["arb_exists"],
        "roi_pct": stakes["roi_pct"],
        "guaranteed_profit": stakes["guaranteed_profit"],
        "f1_name": odds_data.get("fighter1", f1_name),
        "f2_name": odds_data.get("fighter2", f2_name),
        "f1_stake": stakes["f1_stake"],
        "f2_stake": stakes["f2_stake"],
        "f1_book": f1_book,
        "f2_book": f2_book,
        "f1_odds": f1_odds,
        "f2_odds": f2_odds,
        "total_stake": stakes["total_stake"],
        "annotated_books": annotated,
    }


if __name__ == "__main__":
    # Quick demo
    print("=== Arb Example: +150 vs +130 ===")
    arb = find_arb_pct(150, 130)
    print(f"Arb %: {arb:.2f}%")
    s = calculate_stakes(150, 130, 100)
    print(f"Stakes: F1=${s['f1_stake']}, F2=${s['f2_stake']}")
    print(f"Guaranteed profit: ${s['guaranteed_profit']}, ROI: {s['roi_pct']}%")

    print("\n=== No Arb Example: -200 vs +150 ===")
    arb2 = find_arb_pct(-200, 150)
    print(f"Arb %: {arb2:.2f}%")
    s2 = calculate_stakes(-200, 150, 100)
    print(f"Stakes: F1=${s2['f1_stake']}, F2=${s2['f2_stake']}")
    print(f"Guaranteed profit: ${s2['guaranteed_profit']}, ROI: {s2['roi_pct']}%")
