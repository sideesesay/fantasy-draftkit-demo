"""Synthetic, session-only mock draft with automated fictional opponents."""

import random

import streamlit as st

from draftlab.data import load_players
from draftlab.logic import (
    LINEUP_PRESETS,
    MOCK_VARIATIONS,
    next_open_pick,
    recommend_players,
    roster_for_team,
    simulate_mock_until_user_pick,
    snake_team_for_pick,
    tracker_grid,
)
from draftlab.ui import (
    assign_mock_player,
    clear_mock_draft,
    mock_settings,
    player_option,
    reconcile_mock_board_dimensions,
)


st.title("Mock draft")
st.caption(
    "Practice against fictional opponents on a board that is isolated from the manual draft tracker."
)
players = load_players()

with st.container(border=True):
    st.subheader("Practice setup")
    size_column, slot_column = st.columns(2)
    with size_column:
        st.segmented_control(
            "League size",
            [8, 10, 12],
            key="mock_league_size",
            persist_state="session",
        )
    if int(st.session_state.mock_draft_slot) > int(st.session_state.mock_league_size):
        st.session_state.mock_draft_slot = int(st.session_state.mock_league_size)
    with slot_column:
        st.number_input(
            "Your draft slot",
            min_value=1,
            max_value=int(st.session_state.mock_league_size),
            step=1,
            key="mock_draft_slot",
            persist_state="session",
        )

    rounds_column, lineup_column = st.columns(2)
    with rounds_column:
        st.number_input(
            "Draft rounds",
            min_value=6,
            max_value=16,
            step=1,
            key="mock_draft_rounds",
            persist_state="session",
        )
    with lineup_column:
        st.segmented_control(
            "Lineup",
            list(LINEUP_PRESETS),
            key="mock_lineup_preset",
            persist_state="session",
        )
    st.segmented_control(
        "Opponent variation",
        list(MOCK_VARIATIONS),
        key="mock_variation",
        persist_state="session",
        help=(
            "Opponent selections stay near the best fictional market pick: "
            "Low uses a 3-pick window, Medium 6, and High 10."
        ),
    )

if reconcile_mock_board_dimensions():
    st.toast("The practice format changed, so only the temporary mock board was cleared.")

config = mock_settings()
board = dict(st.session_state.mock_draft_board)
league_pick = next_open_pick(board, config["league_size"], config["rounds"])
user_pick = next_open_pick(
    board,
    config["league_size"],
    config["rounds"],
    team_slot=config["draft_slot"],
)
mock_roster = roster_for_team(
    players,
    board,
    config["draft_slot"],
    config["league_size"],
)

with st.container(horizontal=True):
    st.metric("Next league pick", league_pick or "Complete", border=True)
    st.metric("Your next pick", user_pick or "Complete", border=True)
    st.metric("Your mock roster", len(mock_roster), border=True)
    st.metric(
        "Mock progress",
        f"{len(board)}/{config['league_size'] * config['rounds']}",
        border=True,
    )

variation_window = {"Low": 3, "Medium": 6, "High": 10}[config["variation"]]
st.info(
    f"Fictional opponents sample within {variation_window} synthetic market-pick spots of the "
    "best available profile. Lower market picks remain more likely, and simulation always stops "
    "before your selection.",
    icon=":material/casino:",
)


@st.dialog("Reset the mock draft")
def confirm_mock_reset() -> None:
    st.write("This clears only the temporary practice board. The manual tracker is unchanged.")
    if st.button(
        "Start a new mock",
        type="primary",
        icon=":material/restart_alt:",
        key="confirm_mock_reset",
    ):
        clear_mock_draft(advance_seed=True)
        st.rerun()


with st.container(horizontal=True):
    if st.button(
        "Auto-draft to my next pick",
        type="primary",
        icon=":material/fast_forward:",
        key="mock_auto_draft",
        disabled=league_pick is None,
    ):
        rng = random.Random(config["seed"] + int(st.session_state.mock_auto_runs) * 10_007)
        updated_board, drafted, next_user_pick = simulate_mock_until_user_pick(
            players,
            board,
            config["league_size"],
            config["rounds"],
            config["draft_slot"],
            variation=config["variation"],
            rng=rng,
        )
        st.session_state.mock_draft_board = updated_board
        st.session_state.mock_auto_runs += 1
        if drafted:
            st.session_state.mock_notice = (
                f"Auto-drafted {drafted} fictional opponent pick(s). "
                f"Your next pick is {next_user_pick}."
            )
        elif next_user_pick:
            st.session_state.mock_notice = f"It is already your turn at pick {next_user_pick}."
        else:
            st.session_state.mock_notice = "The synthetic practice board is complete."
        st.rerun()
    if st.button(
        "Start a fresh mock",
        type="tertiary",
        icon=":material/restart_alt:",
        key="mock_reset",
    ):
        confirm_mock_reset()

notice = st.session_state.pop("mock_notice", None)
if notice:
    st.success(notice)

board = dict(st.session_state.mock_draft_board)
league_pick = next_open_pick(board, config["league_size"], config["rounds"])
user_pick = next_open_pick(
    board,
    config["league_size"],
    config["rounds"],
    team_slot=config["draft_slot"],
)
ready_for_user = league_pick is not None and league_pick == user_pick

st.subheader("Make your selection")
if user_pick is None:
    st.success("Your configured practice selections are complete.", icon=":material/check_circle:")
elif not ready_for_user:
    owner = snake_team_for_pick(league_pick, config["league_size"]) if league_pick else None
    st.write(
        f"Team {owner} is next at pick {league_pick}. Use auto-draft to advance the fictional opponents."
    )
else:
    recommendations = recommend_players(
        players,
        set(board.values()),
        mock_roster,
        user_pick,
        config["lineup"],
        limit=12,
    )
    if recommendations.empty:
        st.warning("No fictional players remain available.")
    else:
        recommendation_table = recommendations[
            [
                "player_name",
                "position",
                "model_rank",
                "market_pick",
                "value_delta",
                "fit_score",
                "roster_need",
            ]
        ].rename(
            columns={
                "player_name": "Demo player",
                "position": "Pos",
                "model_rank": "Rank",
                "market_pick": "Market pick",
                "value_delta": "Value",
                "fit_score": "Fit score",
                "roster_need": "Roster fit",
            }
        )
        st.dataframe(
            recommendation_table,
            hide_index=True,
            column_config={
                "Rank": st.column_config.NumberColumn(format="%d"),
                "Market pick": st.column_config.NumberColumn(format="%.1f"),
                "Value": st.column_config.NumberColumn(format="%+.1f"),
                "Fit score": st.column_config.NumberColumn(format="%.1f"),
            },
        )
        selected_id = st.selectbox(
            f"Your selection at pick {user_pick}",
            recommendations["player_id"].tolist(),
            format_func=lambda player_id: player_option(player_id, players),
            key="mock_player_choice",
            persist_state="page",
        )
        if st.button(
            "Draft for my mock roster",
            type="primary",
            icon=":material/add_circle:",
            key="mock_make_pick",
        ):
            ok, message = assign_mock_player(selected_id, user_pick)
            (st.toast if ok else st.warning)(message)
            if ok:
                st.rerun()

st.subheader("Practice board")
grid = tracker_grid(
    players,
    st.session_state.mock_draft_board,
    config["league_size"],
    config["rounds"],
    config["draft_slot"],
)
st.dataframe(grid, hide_index=True, height=min(620, 40 + config["rounds"] * 36))

st.subheader("Your mock roster")
mock_roster = roster_for_team(
    players,
    st.session_state.mock_draft_board,
    config["draft_slot"],
    config["league_size"],
)
if mock_roster.empty:
    st.caption("No practice selections yet.")
else:
    roster_table = mock_roster[
        ["pick", "player_name", "club", "position", "model_rank", "market_pick", "value_delta"]
    ].rename(
        columns={
            "pick": "Pick",
            "player_name": "Demo player",
            "club": "Demo club",
            "position": "Pos",
            "model_rank": "Rank",
            "market_pick": "Market pick",
            "value_delta": "Value",
        }
    )
    st.dataframe(
        roster_table,
        hide_index=True,
        column_config={
            "Pick": st.column_config.NumberColumn(format="%d"),
            "Rank": st.column_config.NumberColumn(format="%d"),
            "Market pick": st.column_config.NumberColumn(format="%.1f"),
            "Value": st.column_config.NumberColumn(format="%+.1f"),
        },
    )

st.caption(
    "Mock picks live only in temporary app-session memory and never change the manual draft board."
)
