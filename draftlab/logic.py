"""Pure draft, recommendation, roster, and tracker calculations."""

from __future__ import annotations

import math
import random
from collections.abc import Collection, Mapping
from typing import Any

import pandas as pd


LINEUP_PRESETS: dict[str, dict[str, int]] = {
    "Classic": {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1},
    "Double flex": {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 2},
}
SKILL_POSITIONS = {"RB", "WR", "TE"}
MOCK_VARIATIONS = ("Low", "Medium", "High")
MOCK_VARIATION_WINDOWS: dict[str, tuple[float, float]] = {
    "Low": (3.0, 2.0),
    "Medium": (6.0, 4.0),
    "High": (10.0, 7.0),
}


def snake_team_for_pick(pick: int, team_count: int) -> int:
    """Return the one-based team slot owning an overall snake-draft pick."""
    if pick < 1 or team_count < 2:
        raise ValueError("Pick must be positive and team count must be at least two.")
    round_index, within_round = divmod(pick - 1, team_count)
    if round_index % 2 == 0:
        return within_round + 1
    return team_count - within_round


def pick_for_team(round_number: int, team_slot: int, team_count: int) -> int:
    """Return the overall pick assigned to a team in a given round."""
    if round_number < 1 or not 1 <= team_slot <= team_count:
        raise ValueError("Round and team slot are outside the draft board.")
    offset = team_slot if round_number % 2 else team_count - team_slot + 1
    return (round_number - 1) * team_count + offset


def next_open_pick(
    assignments: Mapping[int, str],
    team_count: int,
    rounds: int,
    team_slot: int | None = None,
) -> int | None:
    """Return the earliest unfilled pick, optionally restricted to one team."""
    maximum = team_count * rounds
    for pick in range(1, maximum + 1):
        if pick in assignments:
            continue
        if team_slot is None or snake_team_for_pick(pick, team_count) == team_slot:
            return pick
    return None


def mock_team_position_counts(
    players: pd.DataFrame,
    assignments: Mapping[int, str],
    team_slot: int,
    team_count: int,
) -> dict[str, int]:
    """Count one fictional mock team's QB/RB/WR/TE selections."""
    roster = roster_for_team(players, assignments, team_slot, team_count)
    counts = roster["position"].value_counts().to_dict() if not roster.empty else {}
    return {position: int(counts.get(position, 0)) for position in ("QB", "RB", "WR", "TE")}


def mock_position_weight(
    position: Any,
    counts: Mapping[str, int],
    lineup: Mapping[str, int],
) -> float:
    """Return a roster-aware weight for a fictional opponent candidate.

    The guardrails work only inside the existing synthetic Market-ADP cluster.
    They prevent obvious positional over-drafting while leaving opponent picks
    probabilistic and market-led.
    """
    position = str(position).upper()
    if position not in {"QB", "RB", "WR", "TE"}:
        return 1.0
    required = {key: int(lineup.get(key, 0)) for key in ("QB", "RB", "WR", "TE")}
    flex_slots = int(lineup.get("FLEX", 0))
    flex_used = sum(max(int(counts.get(key, 0)) - required[key], 0) for key in SKILL_POSITIONS)
    open_flex = max(flex_slots - flex_used, 0)

    if position in {"QB", "TE"}:
        if int(counts.get(position, 0)) >= 2:
            return 0.0
        return 2.2 if int(counts.get(position, 0)) < required[position] else 0.35

    other = "WR" if position == "RB" else "RB"
    own_count, other_count = int(counts.get(position, 0)), int(counts.get(other, 0))
    basic_need = max(required[position], 1 if flex_slots else 0)
    other_basic_need = max(required[other], 1 if flex_slots else 0)
    if other_count == 0 and own_count >= basic_need and other_basic_need:
        return 0.0
    if own_count < required[position]:
        return 2.2
    if open_flex:
        return 1.35 + (0.20 * flex_slots)
    return 0.85


def mock_best_available_player(
    players: pd.DataFrame,
    drafted_ids: Collection[str],
    variation: str = "Medium",
    rng: random.Random | None = None,
    team_slot: int | None = None,
    assignments: Mapping[int, str] | None = None,
    team_count: int | None = None,
    lineup: Mapping[str, int] | None = None,
) -> str | None:
    """Choose a market-led fictional opponent pick with roster guardrails."""
    available = players[~players["player_id"].isin(set(drafted_ids))].copy()
    if available.empty:
        return None

    available["_market_pick"] = pd.to_numeric(available["market_pick"], errors="coerce")
    available["_model_rank"] = pd.to_numeric(available["model_rank"], errors="coerce")
    available = available.sort_values(
        ["_market_pick", "_model_rank", "player_id"],
        na_position="last",
        kind="stable",
    )
    if rng is None or available["_market_pick"].notna().sum() < 2:
        return str(available.iloc[0].player_id)

    window, spread = MOCK_VARIATION_WINDOWS.get(
        variation,
        MOCK_VARIATION_WINDOWS["Medium"],
    )
    market_available = available[available["_market_pick"].notna()].copy()
    best_market_pick = float(market_available.iloc[0]["_market_pick"])
    candidate_pool = market_available[
        market_available["_market_pick"] <= best_market_pick + window
    ].copy()
    candidate_pool["_mock_weight"] = [
        math.exp(-((float(market_pick) - best_market_pick) / spread))
        for market_pick in candidate_pool["_market_pick"]
    ]
    if all(value is not None for value in (team_slot, assignments, team_count, lineup)):
        counts = mock_team_position_counts(players, assignments or {}, int(team_slot), int(team_count))
        candidate_pool["_position_weight"] = candidate_pool["position"].map(
            lambda position: mock_position_weight(position, counts, lineup or {})
        )
        eligible_pool = candidate_pool[candidate_pool["_position_weight"] > 0].copy()
        # If an exceptionally narrow ADP cluster contains only capped
        # positions, retain it instead of inventing a player outside the
        # selected synthetic market window.
        if not eligible_pool.empty:
            candidate_pool = eligible_pool
            candidate_pool["_mock_weight"] *= candidate_pool["_position_weight"]
    return str(
        rng.choices(
            candidate_pool["player_id"].tolist(),
            weights=candidate_pool["_mock_weight"].tolist(),
            k=1,
        )[0]
    )


def simulate_mock_until_user_pick(
    players: pd.DataFrame,
    assignments: Mapping[int, str],
    team_count: int,
    rounds: int,
    user_slot: int,
    variation: str = "Medium",
    rng: random.Random | None = None,
    lineup: Mapping[str, int] | None = None,
) -> tuple[dict[int, str], int, int | None]:
    """Fill open opponent picks in order and stop before the user's next pick."""
    if not 1 <= user_slot <= team_count:
        raise ValueError("The mock user slot must be on the draft board.")
    board = {int(pick): player_id for pick, player_id in assignments.items()}
    drafted_ids = set(board.values())
    mock_rng = rng or random.Random()
    active_lineup = lineup or LINEUP_PRESETS["Classic"]
    drafted = 0
    maximum = team_count * rounds

    for pick in range(1, maximum + 1):
        if pick in board:
            continue
        if snake_team_for_pick(pick, team_count) == user_slot:
            return dict(sorted(board.items())), drafted, pick
        player_id = mock_best_available_player(
            players,
            drafted_ids,
            variation=variation,
            rng=mock_rng,
            team_slot=snake_team_for_pick(pick, team_count),
            assignments=board,
            team_count=team_count,
            lineup=active_lineup,
        )
        if player_id is None:
            break
        board[pick] = player_id
        drafted_ids.add(player_id)
        drafted += 1

    return dict(sorted(board.items())), drafted, None


def roster_for_team(
    players: pd.DataFrame,
    assignments: Mapping[int, str],
    team_slot: int,
    team_count: int,
) -> pd.DataFrame:
    """Return one fictional team's drafted players with their pick numbers."""
    picks = [
        {"pick": pick, "player_id": player_id}
        for pick, player_id in assignments.items()
        if snake_team_for_pick(int(pick), team_count) == team_slot
    ]
    if not picks:
        return players.iloc[0:0].assign(pick=pd.Series(dtype="int64"))
    pick_frame = pd.DataFrame(picks)
    return (
        pick_frame.merge(players, on="player_id", how="inner")
        .sort_values("pick")
        .reset_index(drop=True)
    )


def roster_needs(roster: pd.DataFrame, lineup: Mapping[str, int]) -> dict[str, int]:
    """Calculate open direct starters plus flexible skill-position openings."""
    counts = roster["position"].value_counts().to_dict() if not roster.empty else {}
    needs = {
        position: max(int(lineup.get(position, 0)) - int(counts.get(position, 0)), 0)
        for position in ("QB", "RB", "WR", "TE")
    }
    direct_skill_filled = sum(
        min(int(counts.get(position, 0)), int(lineup.get(position, 0)))
        for position in SKILL_POSITIONS
    )
    skill_count = sum(int(counts.get(position, 0)) for position in SKILL_POSITIONS)
    extra_skill_players = max(skill_count - direct_skill_filled, 0)
    needs["FLEX"] = max(int(lineup.get("FLEX", 0)) - extra_skill_players, 0)
    return needs


def market_timing_score(actual_pick: float, market_pick: float, team_count: int) -> float:
    """Score a fictional pick price against the supplied synthetic market."""
    delta = actual_pick - market_pick
    if delta < 0:
        return max(0.0, min(100.0, 75.0 + delta * (35.0 / max(team_count, 1))))
    return max(
        0.0,
        min(
            100.0,
            75.0 + 25.0 * math.exp(-((delta - team_count) / max(team_count, 1)) ** 2),
        ),
    )


def draft_value_at_cost_score(
    value_delta: Any,
    actual_pick: Any,
    market_pick: Any,
    team_count: int,
) -> tuple[float, float | None, bool]:
    """Blend synthetic source value with the fictional price actually paid."""
    value = pd.to_numeric(pd.Series([value_delta]), errors="coerce").iloc[0]
    source_score = max(0.0, min(100.0, 50.0 + float(value) * 3.0)) if pd.notna(value) else 50.0
    actual = pd.to_numeric(pd.Series([actual_pick]), errors="coerce").iloc[0]
    market = pd.to_numeric(pd.Series([market_pick]), errors="coerce").iloc[0]
    if pd.isna(actual) or pd.isna(market):
        return source_score, None, False
    timing = market_timing_score(float(actual), float(market), team_count)
    return max(0.0, min(100.0, source_score * 0.60 + timing * 0.40)), timing, True


def recommend_players(
    players: pd.DataFrame,
    drafted_ids: Collection[str],
    roster: pd.DataFrame,
    current_pick: int,
    lineup: Mapping[str, int],
    target_ids: Collection[str] = (),
    limit: int = 10,
) -> pd.DataFrame:
    """Rank available demo players with transparent, deterministic heuristics."""
    available = players[~players["player_id"].isin(set(drafted_ids))].copy()
    if available.empty:
        return available.assign(
            fit_score=pd.Series(dtype="float64"),
            roster_need=pd.Series(dtype="string"),
            timing=pd.Series(dtype="string"),
            rationale=pd.Series(dtype="string"),
        )

    needs = roster_needs(roster, lineup)
    direct_need = available["position"].map(lambda value: needs.get(value, 0) > 0)
    flex_need = available["position"].isin(SKILL_POSITIONS) & (needs["FLEX"] > 0)
    need_bonus = direct_need.astype(float) * 18.0 + (~direct_need & flex_need).astype(float) * 7.0

    rank_quality = 105.0 - available["model_rank"] * 0.38
    value_bonus = available["value_delta"].clip(-25, 25) * 0.90
    upside_bonus = available["upside"] * 2.20
    stability_bonus = (6 - available["risk"]) * 1.40
    timing_bonus = (10.0 - (available["market_pick"] - current_pick).abs() * 0.35).clip(-8, 10)
    target_bonus = available["player_id"].isin(set(target_ids)).astype(float) * 4.0

    available["fit_score"] = (
        rank_quality
        + value_bonus
        + upside_bonus
        + stability_bonus
        + timing_bonus
        + need_bonus
        + target_bonus
    ).round(1)
    available["roster_need"] = [
        "Direct opening" if is_direct else "Flex opening" if is_flex else "Depth"
        for is_direct, is_flex in zip(direct_need, flex_need, strict=True)
    ]
    available["timing"] = available["market_pick"].map(
        lambda market: "Available now" if market <= current_pick + 8 else "May last"
    )
    available["rationale"] = available.apply(
        lambda row: (
            f"{row['roster_need']}; model rank {int(row['model_rank'])}; "
            f"illustrative value {row['value_delta']:+.1f}."
        ),
        axis=1,
    )
    return (
        available.sort_values(["fit_score", "model_rank"], ascending=[False, True])
        .head(limit)
        .reset_index(drop=True)
    )


def roster_score(
    roster: pd.DataFrame,
    lineup: Mapping[str, int],
    pool_size: int,
    team_count: int = 10,
) -> dict[str, Any]:
    """Grade a fictional roster on quality, coverage, value, upside, and stability."""
    if roster.empty:
        return {
            "score": 0.0,
            "label": "Not started",
            "coverage": 0.0,
            "quality": 0.0,
            "draft_value": 0.0,
            "draft_timing": None,
            "value_timing_count": 0,
            "upside": 0.0,
            "stability": 0.0,
        }

    needs = roster_needs(roster, lineup)
    required = sum(int(value) for value in lineup.values())
    unfilled = sum(needs.values())
    coverage = max(0.0, 100.0 * (required - unfilled) / max(required, 1))
    quality = (
        100.0
        - (roster["model_rank"] - 1) * 100.0 / max(pool_size - 1, 1)
    ).mean()
    value_components = roster.apply(
        lambda row: draft_value_at_cost_score(
            row.get("value_delta"),
            row.get("pick"),
            row.get("market_pick"),
            team_count,
        ),
        axis=1,
    )
    draft_value = float(value_components.map(lambda item: item[0]).mean())
    timing_values = [item[1] for item in value_components if item[1] is not None]
    draft_timing = float(sum(timing_values) / len(timing_values)) if timing_values else None
    value_timing_count = int(sum(item[2] for item in value_components))
    upside = ((roster["upside"].mean() - 1) / 4 * 100).clip(0, 100)
    stability = ((5 - roster["risk"].mean()) / 4 * 100).clip(0, 100)
    score = float(
        0.40 * quality
        + 0.22 * coverage
        + 0.15 * draft_value
        + 0.12 * upside
        + 0.11 * stability
    )
    score = round(max(0.0, min(100.0, score)), 1)
    if score >= 78:
        label = "Strong demo build"
    elif score >= 62:
        label = "Balanced demo build"
    elif score >= 45:
        label = "Developing demo build"
    else:
        label = "Early demo build"
    return {
        "score": score,
        "label": label,
        "coverage": round(float(coverage), 1),
        "quality": round(float(quality), 1),
        "draft_value": round(float(draft_value), 1),
        "draft_timing": round(float(draft_timing), 1) if draft_timing is not None else None,
        "value_timing_count": value_timing_count,
        "upside": round(float(upside), 1),
        "stability": round(float(stability), 1),
    }


def roster_insights(roster: pd.DataFrame, lineup: Mapping[str, int]) -> tuple[list[str], list[str], list[str]]:
    """Return concise synthetic roster strengths, weaknesses, and next steps."""
    if roster.empty:
        return [], ["No fictional player selections are recorded yet."], ["Record a tracker pick to begin the demo roster review."]
    needs = roster_needs(roster, lineup)
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    best_ranked = roster.loc[roster["model_rank"].idxmin()]
    strengths.append(
        f"{best_ranked.player_name} is the best current model-rank anchor (rank {int(best_ranked.model_rank)})."
    )
    if float(roster["value_delta"].mean()) > 0:
        strengths.append("The current roster has positive average synthetic source value.")
    missing = [f"{count} {position}" for position, count in needs.items() if count]
    if missing:
        weaknesses.append("Open lineup needs: " + ", ".join(missing) + ".")
        recommendations.append("Prioritize an available fictional player at an open group before adding more depth.")
    if float(roster["value_delta"].mean()) < 0:
        weaknesses.append("Average synthetic source value is below market; later picks should favor positive-value profiles.")
    if not recommendations:
        recommendations.append("With the demo starting structure filled, use Market Pick versus actual pick to choose the better value profile.")
    return strengths[:2], weaknesses[:2], recommendations[:2]


def tracker_grid(
    players: pd.DataFrame,
    assignments: Mapping[int, str],
    team_count: int,
    rounds: int,
    user_slot: int,
) -> pd.DataFrame:
    """Build a compact snake-board display with no external team identities."""
    names = players.set_index("player_id")["player_name"].to_dict()
    rows: list[dict[str, str | int]] = []
    for round_number in range(1, rounds + 1):
        row: dict[str, str | int] = {"Round": round_number}
        for team_slot in range(1, team_count + 1):
            pick = pick_for_team(round_number, team_slot, team_count)
            label = f"My team ({team_slot})" if team_slot == user_slot else f"Team {team_slot}"
            player_id = assignments.get(pick)
            row[label] = f"{pick}. {names.get(player_id, 'Open')}"
        rows.append(row)
    return pd.DataFrame(rows)


def swap_preview(
    roster: pd.DataFrame,
    give_id: str,
    receive_row: pd.Series,
    lineup: Mapping[str, int],
    pool_size: int,
    team_count: int = 10,
) -> tuple[dict[str, Any], dict[str, Any], pd.DataFrame]:
    """Preview a one-for-one fictional swap without mutating draft state."""
    before = roster_score(roster, lineup, pool_size, team_count)
    after_roster = roster[roster["player_id"] != give_id].copy()
    after_roster = pd.concat([after_roster, receive_row.to_frame().T], ignore_index=True)
    for column in ("model_rank", "upside", "risk"):
        after_roster[column] = pd.to_numeric(after_roster[column], errors="coerce")
    after = roster_score(after_roster, lineup, pool_size, team_count)
    return before, after, after_roster


def validate_backup_payload(
    payload: Any,
    valid_player_ids: Collection[str],
    team_count: int,
    rounds: int,
) -> tuple[dict[int, str], list[str]]:
    """Validate a small synthetic-session backup without trusting browser input."""
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("Unsupported demo backup format.")
    if set(payload) != {"version", "dataset", "settings", "picks", "targets"}:
        raise ValueError("Backup contains unsupported fields.")
    if payload.get("dataset") != "synthetic-draft-lab":
        raise ValueError("This backup was not created by the synthetic demo.")
    settings_payload = payload.get("settings")
    if settings_payload != {"league_size": team_count, "rounds": rounds}:
        raise ValueError("Backup league size and rounds must match the current demo board.")

    valid = set(valid_player_ids)
    raw_picks = payload.get("picks")
    raw_targets = payload.get("targets")
    if not isinstance(raw_picks, list) or not isinstance(raw_targets, list):
        raise ValueError("Backup picks and targets must be lists.")
    if len(raw_picks) > team_count * rounds or len(raw_targets) > len(valid):
        raise ValueError("Backup contains too many records.")

    board: dict[int, str] = {}
    seen_players: set[str] = set()
    for entry in raw_picks:
        if not isinstance(entry, dict):
            raise ValueError("Each backup pick must be an object.")
        if set(entry) != {"pick", "player_id"}:
            raise ValueError("A backup pick contains unsupported fields.")
        pick = entry.get("pick")
        player_id = entry.get("player_id")
        if isinstance(pick, bool) or not isinstance(pick, int):
            raise ValueError("Backup pick numbers must be integers.")
        if not 1 <= pick <= team_count * rounds:
            raise ValueError("Backup contains a pick outside the current board.")
        if not isinstance(player_id, str) or player_id not in valid:
            raise ValueError("Backup references an unknown demo player.")
        if pick in board or player_id in seen_players:
            raise ValueError("Backup pick numbers and demo players must be unique.")
        board[pick] = player_id
        seen_players.add(player_id)

    targets: list[str] = []
    for player_id in raw_targets:
        if not isinstance(player_id, str) or player_id not in valid:
            raise ValueError("Backup target references an unknown demo player.")
        if player_id not in targets:
            targets.append(player_id)
    return dict(sorted(board.items())), targets
