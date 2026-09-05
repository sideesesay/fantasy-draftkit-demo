"""Filter and interact with the fictional draft board."""

import streamlit as st

from draftlab.data import POSITIONS, load_players
from draftlab.ui import assign_to_next_pick, drafted_ids, player_option, toggle_target


players = load_players()
drafted = drafted_ids()
targets = set(st.session_state.targets)

st.title("Draft board")
st.caption("Every identity and metric on this board is fictional and generated locally.")

with st.container(horizontal=True, vertical_alignment="bottom"):
    selected_positions = st.pills(
        "Positions",
        list(POSITIONS),
        default=list(POSITIONS),
        selection_mode="multi",
        key="board_positions",
        persist_state="page",
    )
    selected_tiers = st.multiselect(
        "Tiers",
        players["tier"].drop_duplicates().tolist(),
        default=players["tier"].drop_duplicates().tolist(),
        key="board_tiers",
        persist_state="page",
    )
    search = st.text_input(
        "Search fictional players",
        placeholder="Try Demo Axiom",
        key="board_search",
        persist_state="page",
    )
    available_only = st.toggle(
        "Available only",
        value=True,
        key="board_available_only",
        persist_state="page",
    )

filtered = players.copy()
if selected_positions:
    filtered = filtered[filtered["position"].isin(selected_positions)]
else:
    filtered = filtered.iloc[0:0]
if selected_tiers:
    filtered = filtered[filtered["tier"].isin(selected_tiers)]
else:
    filtered = filtered.iloc[0:0]
if search.strip():
    filtered = filtered[
        filtered["player_name"].str.contains(search.strip(), case=False, regex=False)
        | filtered["club"].str.contains(search.strip(), case=False, regex=False)
    ]
if available_only:
    filtered = filtered[~filtered["player_id"].isin(drafted)]

pick_by_player = {player_id: pick for pick, player_id in st.session_state.draft_board.items()}
filtered = filtered.copy()
filtered["Status"] = filtered["player_id"].map(
    lambda player_id: (
        f"Drafted · pick {pick_by_player[player_id]}"
        if player_id in drafted
        else "Target"
        if player_id in targets
        else "Available"
    )
)
display = filtered[
    [
        "model_rank",
        "player_name",
        "club",
        "position",
        "market_pick",
        "value_delta",
        "tier",
        "upside",
        "risk",
        "Status",
    ]
].rename(
    columns={
        "model_rank": "Rank",
        "player_name": "Demo player",
        "club": "Demo club",
        "position": "Pos",
        "market_pick": "Market pick",
        "value_delta": "Value",
        "tier": "Tier",
        "upside": "Upside",
        "risk": "Risk",
    }
)

st.dataframe(
    display,
    hide_index=True,
    height=560,
    column_config={
        "Rank": st.column_config.NumberColumn(format="%d", pinned=True),
        "Demo player": st.column_config.TextColumn(pinned=True),
        "Market pick": st.column_config.NumberColumn(format="%.1f"),
        "Value": st.column_config.NumberColumn(format="%+.1f"),
        "Upside": st.column_config.ProgressColumn(min_value=1, max_value=5),
        "Risk": st.column_config.ProgressColumn(min_value=1, max_value=5),
    },
)

st.subheader("Board actions")
action_pool = players.sort_values("model_rank")
selected_id = st.selectbox(
    "Demo player",
    action_pool["player_id"].tolist(),
    format_func=lambda player_id: player_option(player_id, players),
    key="board_action_player",
    persist_state="page",
)

with st.container(horizontal=True):
    target_label = "Remove target" if selected_id in targets else "Save target"
    if st.button(target_label, icon=":material/bookmark:"):
        is_target = toggle_target(selected_id)
        st.toast("Target saved." if is_target else "Target removed.")
        st.rerun()
    if st.button(
        "Draft at next open league pick",
        icon=":material/add_circle:",
        type="primary",
        disabled=selected_id in drafted,
    ):
        ok, message = assign_to_next_pick(selected_id)
        (st.toast if ok else st.warning)(message)
        if ok:
            st.rerun()
