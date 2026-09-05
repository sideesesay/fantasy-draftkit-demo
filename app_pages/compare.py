"""Side-by-side fictional player comparison."""

import pandas as pd
import streamlit as st

from draftlab.data import load_history, load_players
from draftlab.logic import roster_for_team, roster_insights, roster_needs, roster_score
from draftlab.ui import player_option, settings


players = load_players()
history = load_history()
config = settings()
player_ids = players["player_id"].tolist()

comparison_mode = st.segmented_control(
    "Comparison mode",
    ["Players", "Teams"],
    key="compare_mode",
    persist_state="page",
)


def render_team_comparison_panel(team_slot: int) -> None:
    """Render one tracker-synced fictional roster comparison panel."""
    team_label = "My team" if team_slot == config["draft_slot"] else f"Team {team_slot}"
    roster = roster_for_team(players, st.session_state.draft_board, team_slot, config["league_size"])
    with st.container(border=True):
        st.subheader(team_label)
        st.caption("Read directly from the temporary manual Draft Tracker.")
        if roster.empty:
            st.info("No fictional player selections tracked yet.")
            return
        review = roster_score(roster, config["lineup"], len(players), config["league_size"])
        metric_columns = st.columns(2)
        metrics = [
            ("Roster score", f"{review['score']:.1f}", review["label"]),
            ("Starter coverage", f"{review['coverage']:.0f}%", None),
            ("Quality", f"{review['quality']:.0f}/100", None),
            ("Draft value", f"{review['draft_value']:.0f}/100", None),
            ("Draft timing", f"{review['draft_timing']:.0f}/100" if review["draft_timing"] is not None else "—", f"{review['value_timing_count']} pick(s)"),
            ("Upside", f"{review['upside']:.0f}/100", None),
            ("Stability", f"{review['stability']:.0f}/100", None),
        ]
        for index, (label, value, delta) in enumerate(metrics):
            metric_columns[index % 2].metric(label, value, delta)
        st.caption("Draft Value: 60% synthetic source value and 40% fictional Market Pick versus the recorded tracker pick.")

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
        st.dataframe(
            pd.DataFrame(
                [{"Position group": position, "Open spots": count} for position, count in needs.items()]
            ),
            hide_index=True,
        )
        strengths, weaknesses, recommendations = roster_insights(roster, config["lineup"])
        strength_col, weakness_col, recommendation_col = st.columns(3)
        with strength_col:
            st.markdown("**Strengths**")
            for item in strengths:
                st.write(f"• {item}")
        with weakness_col:
            st.markdown("**Weaknesses**")
            for item in weaknesses:
                st.write(f"• {item}")
        with recommendation_col:
            st.markdown("**Improve next**")
            for item in recommendations:
                st.write(f"• {item}")

        with st.expander("Draft recap & fictional market value", expanded=False):
            recap = display[["Pick", "Demo player", "Pos", "Market pick", "Value"]].copy()
            recap["Pick vs market"] = recap["Pick"] - recap["Market pick"]
            recap["Pick review"] = recap["Pick vs market"].map(
                lambda delta: "Market fall" if delta >= config["league_size"] * 0.5
                else "At market cost" if delta >= -2 else "Early versus market"
            )
            st.dataframe(
                recap,
                hide_index=True,
                column_config={
                    "Pick": st.column_config.NumberColumn(format="%d"),
                    "Market pick": st.column_config.NumberColumn(format="%.1f"),
                    "Pick vs market": st.column_config.NumberColumn(format="%+.1f"),
                    "Value": st.column_config.NumberColumn(format="%+.1f"),
                },
            )


if comparison_mode == "Teams":
    st.title("Team comparison")
    st.caption("Choose two manual Draft Tracker teams. All fictional roster data, draft cost, and scores update from the current temporary board.")
    slots = list(range(1, config["league_size"] + 1))
    first_default = config["draft_slot"]
    first_col, second_col = st.columns(2)
    first_slot = first_col.selectbox(
        "First tracker team",
        slots,
        index=slots.index(first_default),
        format_func=lambda slot: "My team" if slot == config["draft_slot"] else f"Team {slot}",
        key="compare_team_one",
        persist_state="page",
    )
    second_slots = [slot for slot in slots if slot != first_slot]
    second_default = next((slot for slot in second_slots if slot != first_default), second_slots[0])
    second_slot = second_col.selectbox(
        "Second tracker team",
        second_slots,
        index=second_slots.index(second_default),
        format_func=lambda slot: "My team" if slot == config["draft_slot"] else f"Team {slot}",
        key="compare_team_two",
        persist_state="page",
    )
    left_panel, right_panel = st.columns(2)
    with left_panel:
        render_team_comparison_panel(first_slot)
    with right_panel:
        render_team_comparison_panel(second_slot)
    st.stop()

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
