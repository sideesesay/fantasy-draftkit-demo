"""Fictional roster scoring and one-for-one swap preview."""

import pandas as pd
import streamlit as st

from draftlab.data import load_players
from draftlab.logic import roster_for_team, roster_needs, roster_score, swap_preview
from draftlab.ui import player_option, settings


players = load_players()
config = settings()
roster = roster_for_team(
    players,
    st.session_state.draft_board,
    config["draft_slot"],
    config["league_size"],
)

st.title("Roster lab")
st.caption("Review your session-only demo roster and preview a fictional one-for-one swap.")

if roster.empty:
    st.info("Add a demo player from On the clock or Draft tracker to begin a roster review.")
    st.stop()

review = roster_score(roster, config["lineup"], len(players))
with st.container(horizontal=True):
    st.metric("Roster score", f"{review['score']:.1f}", border=True)
    st.metric("Build", review["label"], border=True)
    st.metric("Starter coverage", f"{review['coverage']:.0f}%", border=True)
    st.metric("Stability", f"{review['stability']:.0f}%", border=True)

display = roster[
    ["pick", "player_name", "club", "position", "model_rank", "market_pick", "value_delta", "tier"]
].rename(
    columns={
        "pick": "Pick",
        "player_name": "Demo player",
        "club": "Demo club",
        "position": "Pos",
        "model_rank": "Rank",
        "market_pick": "Market pick",
        "value_delta": "Value",
        "tier": "Tier",
    }
)
st.dataframe(
    display,
    hide_index=True,
    column_config={
        "Pick": st.column_config.NumberColumn(format="%d"),
        "Rank": st.column_config.NumberColumn(format="%d"),
        "Market pick": st.column_config.NumberColumn(format="%.1f"),
        "Value": st.column_config.NumberColumn(format="%+.1f"),
    },
)

needs = roster_needs(roster, config["lineup"])
need_rows = pd.DataFrame(
    [{"Position group": position, "Open spots": count} for position, count in needs.items()]
)
left, right = st.columns(2)
with left.container(border=True):
    st.subheader("Construction")
    st.dataframe(need_rows, hide_index=True)
with right.container(border=True):
    st.subheader("Next step")
    remaining = [position for position, count in needs.items() if count > 0]
    if remaining:
        st.write("Prioritize an open group: " + ", ".join(remaining) + ".")
    else:
        st.write("The demo starting structure is filled; compare depth and value next.")

st.subheader("Swap preview")
st.caption("This calculation never changes the tracker and makes no claim about a real trade market.")
candidate_pool = players[~players["player_id"].isin(roster["player_id"])]
swap_left, swap_right = st.columns(2)
with swap_left:
    give_id = st.selectbox(
        "Send from demo roster",
        roster["player_id"].tolist(),
        format_func=lambda player_id: player_option(player_id, players),
        key="swap_give",
        persist_state="page",
    )
with swap_right:
    receive_id = st.selectbox(
        "Receive for preview",
        candidate_pool["player_id"].tolist(),
        format_func=lambda player_id: player_option(player_id, players),
        key="swap_receive",
        persist_state="page",
    )

receive_row = players.loc[players["player_id"] == receive_id].iloc[0]
before, after, _ = swap_preview(
    roster,
    give_id,
    receive_row,
    config["lineup"],
    len(players),
)
delta = after["score"] - before["score"]
with st.container(horizontal=True):
    st.metric("Before", f"{before['score']:.1f}", border=True)
    st.metric("After", f"{after['score']:.1f}", delta=f"{delta:+.1f}", border=True)
    st.metric("Coverage after", f"{after['coverage']:.0f}%", border=True)
