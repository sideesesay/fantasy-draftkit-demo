"""Public demo overview page."""

import streamlit as st

from draftlab.data import load_history, load_players
from draftlab.ui import drafted_ids


players = load_players()
history = load_history()

with st.container(horizontal=True, vertical_alignment="center"):
    st.title("Synthetic Draft Lab")
    st.badge("Synthetic data", icon=":material/check_circle:", color="green")

st.write(
    "A portfolio-ready fantasy draft simulator built entirely from deterministic, "
    "fictional records. It demonstrates data modeling and interactive decision support "
    "without redistributing rankings, statistics, news, images, or identities from a third party."
)

with st.container(horizontal=True):
    st.metric("Demo players", f"{len(players):,}", border=True)
    st.metric("Fictional history rows", f"{len(history):,}", border=True)
    st.metric("External data calls", "0", border=True)
    st.metric("Drafted this session", len(drafted_ids()), border=True)

left, right = st.columns([1, 2])
with left:
    with st.container(border=True):
        st.subheader("Pool by position")
        counts = (
            players.groupby("position", as_index=False)
            .size()
            .rename(columns={"position": "Position", "size": "Players"})
        )
        st.bar_chart(counts, x="Position", y="Players")

with right:
    with st.container(border=True):
        st.subheader("Top fictional profiles")
        preview = players.head(12)[
            ["model_rank", "player_name", "club", "position", "market_pick", "value_delta", "tier"]
        ].rename(
            columns={
                "model_rank": "Rank",
                "player_name": "Demo player",
                "club": "Demo club",
                "position": "Pos",
                "market_pick": "Market pick",
                "value_delta": "Value",
                "tier": "Tier",
            }
        )
        st.dataframe(
            preview,
            hide_index=True,
            column_config={
                "Rank": st.column_config.NumberColumn(format="%d"),
                "Market pick": st.column_config.NumberColumn(format="%.1f"),
                "Value": st.column_config.NumberColumn(format="%+.1f"),
            },
        )

with st.container(border=True):
    st.subheader("What this public build demonstrates")
    st.markdown(
        """
        - Deterministic ranking and value calculations over a validated local dataset.
        - A stateful snake-draft tracker that stays inside the current temporary app session.
        - An isolated mock draft with synthetic opponent behavior and adjustable variation.
        - Roster-aware recommendations, player comparisons, swap previews, and projection ranges.
        - Fail-closed dataset validation and automated public-safety checks.
        """
    )
    st.caption("The numbers are illustrative software fixtures, not sports advice or real-world forecasts.")
