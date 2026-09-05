"""Load and validate the fictional datasets bundled with the public demo."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAYER_DATA_PATH = PROJECT_ROOT / "data" / "synthetic_players.csv"
HISTORY_DATA_PATH = PROJECT_ROOT / "data" / "synthetic_history.csv"

POSITIONS = ("QB", "RB", "WR", "TE")
PLAYER_COLUMNS = {
    "player_id",
    "player_name",
    "club",
    "position",
    "model_rank",
    "market_pick",
    "value_delta",
    "tier",
    "projected_points",
    "projection_low",
    "projection_high",
    "upside",
    "floor",
    "risk",
    "profile",
    "is_synthetic",
}
HISTORY_COLUMNS = {
    "player_id",
    "season_index",
    "season_label",
    "games",
    "points",
    "points_per_game",
    "opportunities_per_game",
    "is_synthetic",
}


def _synthetic_mask(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def validate_players(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a normalized player frame or fail closed on unsafe input."""
    missing = PLAYER_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Synthetic player data is missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Synthetic player data cannot be empty.")
    if not _synthetic_mask(frame["is_synthetic"]).all():
        raise ValueError("Every bundled player row must be explicitly synthetic.")
    if not frame["player_name"].astype(str).str.startswith("Demo ").all():
        raise ValueError("Every player name must use the Demo naming convention.")
    if not frame["club"].astype(str).str.startswith("Demo Club ").all():
        raise ValueError("Every club name must use the Demo Club naming convention.")
    if frame["player_id"].duplicated().any() or frame["player_name"].duplicated().any():
        raise ValueError("Synthetic player identifiers and names must be unique.")
    if not set(frame["position"]).issubset(POSITIONS):
        raise ValueError("Synthetic player data contains an unsupported position.")

    numeric_columns = [
        "model_rank",
        "market_pick",
        "value_delta",
        "projected_points",
        "projection_low",
        "projection_high",
        "upside",
        "floor",
        "risk",
    ]
    normalized = frame.copy()
    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="raise")
    normalized["model_rank"] = normalized["model_rank"].astype(int)
    expected_ranks = list(range(1, len(normalized) + 1))
    if sorted(normalized["model_rank"].tolist()) != expected_ranks:
        raise ValueError("Model ranks must be contiguous and unique.")
    for column in ("upside", "floor", "risk"):
        if not normalized[column].between(1, 5).all():
            raise ValueError(f"{column} must stay within the illustrative 1-5 scale.")
    if not (normalized["projection_low"] <= normalized["projected_points"]).all():
        raise ValueError("Projection lows cannot exceed the central projection.")
    if not (normalized["projected_points"] <= normalized["projection_high"]).all():
        raise ValueError("Projection highs cannot be below the central projection.")
    normalized["is_synthetic"] = True
    return normalized.sort_values("model_rank").reset_index(drop=True)


def validate_history(frame: pd.DataFrame, valid_player_ids: set[str]) -> pd.DataFrame:
    """Return normalized fictional history tied only to the bundled players."""
    missing = HISTORY_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Synthetic history data is missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Synthetic history data cannot be empty.")
    if not _synthetic_mask(frame["is_synthetic"]).all():
        raise ValueError("Every bundled history row must be explicitly synthetic.")
    if not set(frame["player_id"]).issubset(valid_player_ids):
        raise ValueError("Synthetic history references an unknown player.")

    normalized = frame.copy()
    for column in (
        "season_index",
        "games",
        "points",
        "points_per_game",
        "opportunities_per_game",
    ):
        normalized[column] = pd.to_numeric(normalized[column], errors="raise")
    normalized["season_index"] = normalized["season_index"].astype(int)
    normalized["games"] = normalized["games"].astype(int)
    normalized["is_synthetic"] = True
    if normalized.duplicated(["player_id", "season_index"]).any():
        raise ValueError("Synthetic history contains duplicate player-season rows.")
    return normalized.sort_values(["player_id", "season_index"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_players(path: str | Path = PLAYER_DATA_PATH) -> pd.DataFrame:
    """Load the static fictional draft pool once per app process."""
    return validate_players(pd.read_csv(Path(path)))


@st.cache_data(show_spinner=False)
def load_history(path: str | Path = HISTORY_DATA_PATH) -> pd.DataFrame:
    """Load and validate fictional histories against the fictional player pool."""
    players = load_players()
    return validate_history(pd.read_csv(Path(path)), set(players["player_id"]))
