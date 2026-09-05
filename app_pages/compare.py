"""Side-by-side fictional player comparison."""

import pandas as pd
import streamlit as st

from draftlab.data import load_history, load_players
from draftlab.ui import player_option


players = load_players()
history = load_history()
player_ids = players["player_id"].tolist()

st.title("Compare")
st.caption("Compare two generated profiles and their fictional four-period histories.")

left, right = st.columns(2)
with left:
    first_id = st.selectbox(
        "First demo player",
        player_ids,
        index=0,
        format_func=lambda player_id: player_option(player_id, players),
        key="compare_first",
        persist_state="page",
    )
with right:
    second_id = st.selectbox(
        "Second demo player",
        player_ids,
        index=1,
        format_func=lambda player_id: player_option(player_id, players),
        key="compare_second",
        persist_state="page",
    )

if first_id == second_id:
    st.info("Choose two different demo players to compare.")
    st.stop()

selected = players[players["player_id"].isin([first_id, second_id])].set_index("player_id")
first = selected.loc[first_id]
second = selected.loc[second_id]

for column, row in zip(st.columns(2), [first, second], strict=True):
    with column.container(border=True):
        st.subheader(row.player_name)
        st.caption(f"{row.club} · {row.position} · {row.tier}")
        with st.container(horizontal=True):
            st.metric("Model rank", int(row.model_rank))
            st.metric("Market pick", f"{row.market_pick:.1f}")
            st.metric("Value", f"{row.value_delta:+.1f}")
        st.write(row.profile)

comparison = pd.DataFrame(
    {
        "Metric": ["Projected points", "Projection low", "Projection high", "Upside", "Floor", "Risk"],
        first.player_name: [
            first.projected_points,
            first.projection_low,
            first.projection_high,
            first.upside,
            first.floor,
            first.risk,
        ],
        second.player_name: [
            second.projected_points,
            second.projection_low,
            second.projection_high,
            second.upside,
            second.floor,
            second.risk,
        ],
    }
)
st.dataframe(comparison, hide_index=True)

trend = history[history["player_id"].isin([first_id, second_id])].merge(
    players[["player_id", "player_name"]], on="player_id", how="left"
)
trend_chart = trend.pivot(index="season_index", columns="player_name", values="points_per_game")
st.subheader("Fictional points-per-game history")
st.line_chart(trend_chart, x_label="Demo period", y_label="Illustrative points per game")

rank_leader = first.player_name if first.model_rank < second.model_rank else second.player_name
value_leader = first.player_name if first.value_delta > second.value_delta else second.player_name
st.info(
    f"{rank_leader} leads the generated model rank; {value_leader} leads the generated value measure. "
    "Those signals are intentionally separate for UI testing."
)
