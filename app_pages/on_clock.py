"""Roster-aware recommendations over fictional inputs."""

import streamlit as st

from draftlab.data import load_players
from draftlab.logic import next_open_pick, recommend_players, roster_for_team, roster_needs
from draftlab.ui import assign_player, drafted_ids, player_option, settings, toggle_target


players = load_players()
config = settings()
board = dict(st.session_state.draft_board)
roster = roster_for_team(
    players,
    board,
    config["draft_slot"],
    config["league_size"],
)
your_pick = next_open_pick(
    board,
    config["league_size"],
    config["rounds"],
    team_slot=config["draft_slot"],
)

st.title("On the clock")
st.caption("Transparent demo heuristics combine rank, value, timing, risk, upside, and roster openings.")

if your_pick is None:
    st.success("Your fictional draft slots are filled.", icon=":material/check_circle:")
    st.stop()

needs = roster_needs(roster, config["lineup"])
recommendations = recommend_players(
    players,
    drafted_ids(),
    roster,
    your_pick,
    config["lineup"],
    target_ids=st.session_state.targets,
    limit=10,
)

with st.container(horizontal=True):
    st.metric("Your next pick", your_pick, border=True)
    st.metric("Rostered", len(roster), border=True)
    st.metric("Saved targets", len(st.session_state.targets), border=True)
    open_labels = [key for key, value in needs.items() if value > 0]
    st.metric("Open lineup groups", len(open_labels), border=True)

if open_labels:
    st.caption("Current openings: " + ", ".join(f"{label} × {needs[label]}" for label in open_labels))

if recommendations.empty:
    st.warning("No fictional players remain available.")
    st.stop()

table = recommendations[
    [
        "player_name",
        "position",
        "model_rank",
        "market_pick",
        "value_delta",
        "fit_score",
        "roster_need",
        "timing",
        "rationale",
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
        "timing": "Timing",
        "rationale": "Why",
    }
)
st.dataframe(
    table,
    hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn(format="%d"),
        "Market pick": st.column_config.NumberColumn(format="%.1f"),
        "Value": st.column_config.NumberColumn(format="%+.1f"),
        "Fit score": st.column_config.NumberColumn(format="%.1f"),
    },
)

selected_id = st.selectbox(
    "Recommendation",
    recommendations["player_id"].tolist(),
    format_func=lambda player_id: player_option(player_id, players),
    key="recommendation_player",
    persist_state="page",
)
with st.container(horizontal=True):
    if st.button("Draft for my next pick", type="primary", icon=":material/add_circle:"):
        ok, message = assign_player(selected_id, your_pick)
        (st.toast if ok else st.warning)(message)
        if ok:
            st.rerun()
    if st.button("Toggle saved target", icon=":material/bookmark:"):
        is_target = toggle_target(selected_id)
        st.toast("Target saved." if is_target else "Target removed.")
        st.rerun()

with st.expander("How the fit score works", icon=":material/calculate:"):
    st.write(
        "The score rewards earlier model rank, positive illustrative value, upside, stability, "
        "proximity to the current pick, open lineup groups, and saved targets. It uses no hidden "
        "model and no outside information."
    )
