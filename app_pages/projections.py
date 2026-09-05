"""Explore locally generated fictional histories and projection ranges."""

import streamlit as st

from draftlab.data import load_history, load_players
from draftlab.ui import player_option


players = load_players()
history = load_history()

st.title("Projection lab")
st.caption("These ranges are deterministic fixtures for demonstrating uncertainty-aware UI.")

selected_id = st.selectbox(
    "Demo player",
    players["player_id"].tolist(),
    format_func=lambda player_id: player_option(player_id, players),
    key="projection_player",
    persist_state="page",
)
player = players.loc[players["player_id"] == selected_id].iloc[0]
player_history = history[history["player_id"] == selected_id].sort_values("season_index")

st.subheader(player.player_name)
st.caption(f"{player.club} · {player.position} · {player.tier}")
with st.container(horizontal=True):
    st.metric("Central", f"{player.projected_points:.1f}", border=True)
    st.metric("Low", f"{player.projection_low:.1f}", border=True)
    st.metric("High", f"{player.projection_high:.1f}", border=True)
    st.metric("Range", f"{player.projection_high - player.projection_low:.1f}", border=True)

chart_data = player_history.set_index("season_index")[["points_per_game", "opportunities_per_game"]]
st.line_chart(
    chart_data,
    x_label="Demo period",
    y_label="Illustrative per-period measure",
)

st.dataframe(
    player_history[
        ["season_label", "games", "points", "points_per_game", "opportunities_per_game"]
    ].rename(
        columns={
            "season_label": "Demo period",
            "games": "Games",
            "points": "Points",
            "points_per_game": "Points per game",
            "opportunities_per_game": "Opportunities per game",
        }
    ),
    hide_index=True,
    column_config={
        "Points": st.column_config.NumberColumn(format="%.1f"),
        "Points per game": st.column_config.NumberColumn(format="%.2f"),
        "Opportunities per game": st.column_config.NumberColumn(format="%.2f"),
    },
)

with st.expander("Generation note", icon=":material/science:"):
    st.write(
        "The generator starts from position-specific fictional baselines, applies bounded random "
        "variation from the documented seed, and constructs a low/central/high range from the "
        "generated upside and risk scores. It does not estimate any real person."
    )
