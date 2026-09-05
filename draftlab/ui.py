"""Small Streamlit state helpers shared by the public demo pages."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd
import streamlit as st

from draftlab.logic import (
    LINEUP_PRESETS,
    MOCK_VARIATIONS,
    next_open_pick,
    validate_backup_payload,
)


def initialize_state(valid_player_ids: Iterable[str]) -> None:
    """Initialize all per-session demo state in one place."""
    st.session_state.setdefault("draft_board", {})
    st.session_state.setdefault("targets", [])
    st.session_state.setdefault("event_log", [])
    st.session_state.setdefault("league_size", 10)
    st.session_state.setdefault("draft_slot", 5)
    st.session_state.setdefault("draft_rounds", 12)
    st.session_state.setdefault("lineup_preset", "Classic")
    st.session_state.setdefault("board_signature", None)
    st.session_state.setdefault("mock_draft_board", {})
    st.session_state.setdefault("mock_event_log", [])
    st.session_state.setdefault("mock_league_size", 10)
    st.session_state.setdefault("mock_draft_slot", 5)
    st.session_state.setdefault("mock_draft_rounds", 12)
    st.session_state.setdefault("mock_lineup_preset", "Classic")
    st.session_state.setdefault("mock_variation", "Medium")
    st.session_state.setdefault("mock_board_signature", None)
    st.session_state.setdefault("mock_seed", 20260905)
    st.session_state.setdefault("mock_auto_runs", 0)

    valid = set(valid_player_ids)
    board = {
        int(pick): player_id
        for pick, player_id in dict(st.session_state.draft_board).items()
        if player_id in valid
    }
    st.session_state.draft_board = board
    st.session_state.targets = [
        player_id for player_id in st.session_state.targets if player_id in valid
    ]
    st.session_state.mock_draft_board = {
        int(pick): player_id
        for pick, player_id in dict(st.session_state.mock_draft_board).items()
        if player_id in valid
    }


def settings() -> dict[str, Any]:
    """Return the validated global demo settings."""
    league_size = int(st.session_state.get("league_size", 10))
    draft_slot = min(max(int(st.session_state.get("draft_slot", 1)), 1), league_size)
    rounds = min(max(int(st.session_state.get("draft_rounds", 12)), 1), 16)
    preset = str(st.session_state.get("lineup_preset", "Classic"))
    if preset not in LINEUP_PRESETS:
        preset = "Classic"
    return {
        "league_size": league_size,
        "draft_slot": draft_slot,
        "rounds": rounds,
        "preset": preset,
        "lineup": LINEUP_PRESETS[preset],
    }


def mock_settings() -> dict[str, Any]:
    """Return validated settings for the isolated synthetic practice board."""
    league_size = int(st.session_state.get("mock_league_size", 10))
    if league_size not in {8, 10, 12}:
        league_size = 10
    draft_slot = min(
        max(int(st.session_state.get("mock_draft_slot", 1)), 1),
        league_size,
    )
    rounds = min(max(int(st.session_state.get("mock_draft_rounds", 12)), 6), 16)
    preset = str(st.session_state.get("mock_lineup_preset", "Classic"))
    if preset not in LINEUP_PRESETS:
        preset = "Classic"
    variation = str(st.session_state.get("mock_variation", "Medium"))
    if variation not in MOCK_VARIATIONS:
        variation = "Medium"
    return {
        "league_size": league_size,
        "draft_slot": draft_slot,
        "rounds": rounds,
        "preset": preset,
        "lineup": LINEUP_PRESETS[preset],
        "variation": variation,
        "seed": int(st.session_state.get("mock_seed", 20260905)),
    }


def drafted_ids() -> set[str]:
    return set(dict(st.session_state.draft_board).values())


def player_option(player_id: str, players: pd.DataFrame) -> str:
    row = players.loc[players["player_id"] == player_id].iloc[0]
    return f"{row.player_name} · {row.position} · rank {int(row.model_rank)}"


def assign_player(player_id: str, pick: int) -> tuple[bool, str]:
    board = dict(st.session_state.draft_board)
    if player_id in board.values():
        return False, "That demo player is already on the board."
    if pick in board:
        return False, "That pick is already filled."
    board[int(pick)] = player_id
    st.session_state.draft_board = dict(sorted(board.items()))
    st.session_state.event_log = [*st.session_state.event_log, ("assign", int(pick), player_id)][-50:]
    return True, f"Assigned the demo player to pick {pick}."


def assign_to_next_pick(player_id: str, team_slot: int | None = None) -> tuple[bool, str]:
    config = settings()
    pick = next_open_pick(
        st.session_state.draft_board,
        config["league_size"],
        config["rounds"],
        team_slot=team_slot,
    )
    if pick is None:
        return False, "No open pick remains in that part of the demo board."
    return assign_player(player_id, pick)


def assign_mock_player(player_id: str, pick: int) -> tuple[bool, str]:
    """Assign one fictional player to the isolated mock board."""
    board = dict(st.session_state.mock_draft_board)
    if player_id in board.values():
        return False, "That demo player is already on the mock board."
    if pick in board:
        return False, "That mock pick is already filled."
    board[int(pick)] = player_id
    st.session_state.mock_draft_board = dict(sorted(board.items()))
    st.session_state.mock_event_log = [
        *st.session_state.mock_event_log,
        ("assign", int(pick), player_id),
    ][-50:]
    return True, f"Recorded your fictional selection at pick {pick}."


def remove_pick(pick: int) -> tuple[bool, str]:
    board = dict(st.session_state.draft_board)
    player_id = board.pop(int(pick), None)
    if player_id is None:
        return False, "That pick is already open."
    st.session_state.draft_board = board
    st.session_state.event_log = [*st.session_state.event_log, ("remove", int(pick), player_id)][-50:]
    return True, f"Reopened pick {pick}."


def toggle_target(player_id: str) -> bool:
    targets = list(st.session_state.targets)
    if player_id in targets:
        targets.remove(player_id)
        is_target = False
    else:
        targets.append(player_id)
        is_target = True
    st.session_state.targets = targets
    return is_target


def clear_demo_draft() -> None:
    st.session_state.draft_board = {}
    st.session_state.targets = []
    st.session_state.event_log = []


def clear_mock_draft(advance_seed: bool = False) -> None:
    """Clear only the practice board, leaving the manual board untouched."""
    st.session_state.mock_draft_board = {}
    st.session_state.mock_event_log = []
    st.session_state.mock_auto_runs = 0
    if advance_seed:
        st.session_state.mock_seed = int(st.session_state.mock_seed) + 1


def reconcile_board_dimensions() -> bool:
    """Clear transient picks when board dimensions change to prevent misattribution."""
    config = settings()
    signature = (config["league_size"], config["rounds"])
    previous = st.session_state.get("board_signature")
    changed_with_picks = previous is not None and previous != signature and bool(st.session_state.draft_board)
    if changed_with_picks:
        clear_demo_draft()
    st.session_state.board_signature = signature
    return changed_with_picks


def reconcile_mock_board_dimensions() -> bool:
    """Clear only mock picks when the practice-board dimensions change."""
    config = mock_settings()
    signature = (config["league_size"], config["rounds"], config["draft_slot"])
    previous = st.session_state.get("mock_board_signature")
    changed_with_picks = (
        previous is not None
        and previous != signature
        and bool(st.session_state.mock_draft_board)
    )
    if changed_with_picks:
        clear_mock_draft(advance_seed=True)
    st.session_state.mock_board_signature = signature
    return changed_with_picks


def backup_payload() -> dict[str, Any]:
    """Build a privacy-safe backup containing only fictional IDs and board positions."""
    config = settings()
    return {
        "version": 1,
        "dataset": "synthetic-draft-lab",
        "settings": {
            "league_size": config["league_size"],
            "rounds": config["rounds"],
        },
        "picks": [
            {"pick": int(pick), "player_id": player_id}
            for pick, player_id in sorted(st.session_state.draft_board.items())
        ],
        "targets": list(st.session_state.targets),
    }


def restore_backup(payload: Any, valid_player_ids: Iterable[str]) -> tuple[bool, str]:
    """Validate and restore a synthetic backup into only this app session."""
    config = settings()
    try:
        board, targets = validate_backup_payload(
            payload,
            set(valid_player_ids),
            config["league_size"],
            config["rounds"],
        )
    except ValueError as exc:
        return False, str(exc)
    st.session_state.draft_board = board
    st.session_state.targets = targets
    st.session_state.event_log = []
    return True, f"Restored {len(board)} fictional picks and {len(targets)} targets."
