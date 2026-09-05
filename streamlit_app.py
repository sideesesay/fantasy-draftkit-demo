"""Entrypoint for the public, synthetic-only draft dashboard."""

from __future__ import annotations

import streamlit as st

from draftlab.data import load_players
from draftlab.logic import LINEUP_PRESETS
from draftlab.ui import initialize_state, reconcile_board_dimensions


st.set_page_config(
    page_title="Synthetic Draft Lab",
    page_icon=":material/sports_football:",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    players = load_players()
except (OSError, ValueError) as exc:
    st.error(f"The bundled synthetic dataset failed validation: {exc}")
    st.stop()
initialize_state(players["player_id"])

with st.sidebar:
    st.header("Manual draft setup")
    st.segmented_control(
        "League size",
        [8, 10, 12],
        key="league_size",
        persist_state="session",
    )
    if int(st.session_state.draft_slot) > int(st.session_state.league_size):
        st.session_state.draft_slot = int(st.session_state.league_size)
    st.number_input(
        "Your draft slot",
        min_value=1,
        max_value=int(st.session_state.league_size),
        step=1,
        key="draft_slot",
        persist_state="session",
    )
    st.number_input(
        "Draft rounds",
        min_value=6,
        max_value=16,
        step=1,
        key="draft_rounds",
        persist_state="session",
    )
    st.segmented_control(
        "Lineup",
        list(LINEUP_PRESETS),
        key="lineup_preset",
        persist_state="session",
    )
    st.caption("Temporary app session · fictional records · no external services")

if reconcile_board_dimensions():
    st.toast("Board dimensions changed, so the temporary demo draft was cleared.")

page = st.navigation(
    {
        "": [
            st.Page("app_pages/overview.py", title="Overview", icon=":material/dashboard:", default=True),
        ],
        "Draft": [
            st.Page("app_pages/board.py", title="Draft board", icon=":material/table_chart:"),
            st.Page("app_pages/on_clock.py", title="On the clock", icon=":material/timer:"),
            st.Page("app_pages/tracker.py", title="Draft tracker", icon=":material/view_module:"),
            st.Page("app_pages/mock_draft.py", title="Mock draft", icon=":material/sports_football:"),
        ],
        "Analyze": [
            st.Page("app_pages/compare.py", title="Compare", icon=":material/compare_arrows:"),
            st.Page("app_pages/roster.py", title="Roster lab", icon=":material/groups:"),
            st.Page("app_pages/projections.py", title="Projection lab", icon=":material/query_stats:"),
        ],
        "Project": [
            st.Page("app_pages/methodology.py", title="Methodology", icon=":material/verified_user:"),
        ],
    },
    position="top",
)
page.run()
