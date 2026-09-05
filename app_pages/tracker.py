"""Session-only fictional snake-draft tracker."""

import json

import streamlit as st

from draftlab.data import load_players
from draftlab.logic import next_open_pick, snake_team_for_pick, tracker_grid
from draftlab.ui import (
    assign_player,
    backup_payload,
    clear_demo_draft,
    drafted_ids,
    player_option,
    remove_pick,
    restore_backup,
    settings,
)


players = load_players()
config = settings()
board = dict(st.session_state.draft_board)
open_pick = next_open_pick(board, config["league_size"], config["rounds"])

st.title("Draft tracker")
st.caption(
    "The board stays in temporary app-session memory; this code neither writes it to disk nor "
    "sends it to an external service."
)

if open_pick is not None:
    owner = snake_team_for_pick(open_pick, config["league_size"])
    owner_label = "My team" if owner == config["draft_slot"] else f"Team {owner}"
    with st.container(horizontal=True):
        st.metric("Next open pick", open_pick, border=True)
        st.metric("On the clock", owner_label, border=True)
        st.metric("Board progress", f"{len(board)}/{config['league_size'] * config['rounds']}", border=True)

    available = players[~players["player_id"].isin(drafted_ids())]
    selected_id = st.selectbox(
        "Available demo player",
        available["player_id"].tolist(),
        format_func=lambda player_id: player_option(player_id, players),
        key="tracker_player",
        persist_state="page",
    )
    if st.button("Record next pick", type="primary", icon=":material/add_circle:"):
        ok, message = assign_player(selected_id, open_pick)
        (st.toast if ok else st.warning)(message)
        if ok:
            st.rerun()
else:
    st.success("The fictional board is complete.", icon=":material/check_circle:")

with st.container(horizontal=True):
    filled_picks = sorted(board)
    pick_to_remove = st.selectbox(
        "Filled pick",
        filled_picks,
        format_func=lambda pick: f"Pick {pick}: {players.set_index('player_id').loc[board[pick], 'player_name']}",
        disabled=not filled_picks,
        key="tracker_remove_pick",
        persist_state="page",
    )
    if st.button("Reopen selected pick", icon=":material/undo:", disabled=not filled_picks):
        ok, message = remove_pick(int(pick_to_remove))
        (st.toast if ok else st.warning)(message)
        if ok:
            st.rerun()


@st.dialog("Reset the demo draft")
def confirm_reset() -> None:
    st.write("This clears all temporary picks and saved targets in the current browser session.")
    if st.button("Reset", type="primary", icon=":material/restart_alt:"):
        clear_demo_draft()
        st.rerun()


if st.button("Reset demo draft", type="tertiary", icon=":material/restart_alt:"):
    confirm_reset()

with st.expander("Session backup", icon=":material/download:"):
    st.caption("Backups contain only fictional IDs, pick numbers, settings, and target IDs.")
    backup_text = json.dumps(backup_payload(), indent=2) + "\n"
    st.download_button(
        "Download backup",
        data=backup_text,
        file_name="synthetic_draft_backup.json",
        mime="application/json",
        icon=":material/download:",
        on_click="ignore",
    )
    upload = st.file_uploader(
        "Restore backup",
        type=["json"],
        max_upload_size=1,
        key="tracker_backup_upload",
    )
    if upload is not None and st.button("Validate and restore", icon=":material/upload:"):
        try:
            payload = json.loads(upload.getvalue().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            st.error("The uploaded file is not valid UTF-8 JSON.")
        else:
            ok, message = restore_backup(payload, players["player_id"])
            (st.toast if ok else st.error)(message)
            if ok:
                st.rerun()

grid = tracker_grid(
    players,
    st.session_state.draft_board,
    config["league_size"],
    config["rounds"],
    config["draft_slot"],
)
st.dataframe(grid, hide_index=True, height=min(620, 40 + config["rounds"] * 36))
