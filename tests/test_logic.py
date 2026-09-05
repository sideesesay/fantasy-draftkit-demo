from __future__ import annotations

import random
import unittest
from pathlib import Path

import pandas as pd

from draftlab.data import validate_players
from draftlab.logic import (
    LINEUP_PRESETS,
    mock_best_available_player,
    next_open_pick,
    pick_for_team,
    recommend_players,
    roster_for_team,
    roster_needs,
    roster_score,
    simulate_mock_until_user_pick,
    snake_team_for_pick,
    tracker_grid,
    validate_backup_payload,
)


ROOT = Path(__file__).resolve().parents[1]


class DraftLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.players = validate_players(pd.read_csv(ROOT / "data" / "synthetic_players.csv"))

    def test_snake_order_and_inverse_pick_mapping(self) -> None:
        self.assertEqual(
            [snake_team_for_pick(pick, 4) for pick in range(1, 9)],
            [1, 2, 3, 4, 4, 3, 2, 1],
        )
        for round_number in range(1, 6):
            for team_slot in range(1, 5):
                pick = pick_for_team(round_number, team_slot, 4)
                self.assertEqual(snake_team_for_pick(pick, 4), team_slot)

    def test_next_open_pick_can_follow_one_team(self) -> None:
        board = {1: "SYN-001", 2: "SYN-002", 4: "SYN-004"}
        self.assertEqual(next_open_pick(board, 4, 3), 3)
        self.assertEqual(next_open_pick(board, 4, 3, team_slot=1), 8)

    def test_mock_opponent_pick_stays_in_the_synthetic_market_window(self) -> None:
        board = pd.DataFrame(
            [
                {"player_id": "SYN-001", "market_pick": 1.0, "model_rank": 4},
                {"player_id": "SYN-002", "market_pick": 2.0, "model_rank": 2},
                {"player_id": "SYN-003", "market_pick": 3.0, "model_rank": 1},
                {"player_id": "SYN-004", "market_pick": 50.0, "model_rank": 3},
            ]
        )
        self.assertEqual(mock_best_available_player(board, set()), "SYN-001")
        selected = mock_best_available_player(
            board,
            set(),
            variation="Low",
            rng=random.Random(42),
        )
        self.assertIn(selected, {"SYN-001", "SYN-002", "SYN-003"})

    def test_mock_simulation_stops_before_the_users_snake_pick(self) -> None:
        board, drafted, user_pick = simulate_mock_until_user_pick(
            self.players,
            {},
            team_count=10,
            rounds=12,
            user_slot=3,
            variation="Medium",
            rng=random.Random(7),
        )
        self.assertEqual((drafted, user_pick), (2, 3))
        self.assertEqual(set(board), {1, 2})
        self.assertEqual(len(set(board.values())), 2)

    def test_roster_needs_and_score_are_bounded(self) -> None:
        assignments = {
            1: self.players.iloc[0].player_id,
            8: self.players.iloc[10].player_id,
        }
        roster = roster_for_team(self.players, assignments, team_slot=1, team_count=4)
        needs = roster_needs(roster, LINEUP_PRESETS["Classic"])
        self.assertEqual(set(needs), {"QB", "RB", "WR", "TE", "FLEX"})
        review = roster_score(roster, LINEUP_PRESETS["Classic"], len(self.players))
        self.assertGreaterEqual(review["score"], 0)
        self.assertLessEqual(review["score"], 100)

    def test_flex_openings_do_not_double_count_direct_starters(self) -> None:
        empty_roster = self.players.iloc[0:0]
        self.assertEqual(
            roster_needs(empty_roster, LINEUP_PRESETS["Classic"]),
            {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1},
        )

        three_running_backs = self.players[self.players["position"] == "RB"].head(3)
        needs = roster_needs(three_running_backs, LINEUP_PRESETS["Classic"])
        self.assertEqual(needs, {"QB": 1, "RB": 0, "WR": 2, "TE": 1, "FLEX": 0})
        review = roster_score(three_running_backs, LINEUP_PRESETS["Classic"], len(self.players))
        self.assertAlmostEqual(review["coverage"], 42.9)

    def test_recommendations_exclude_drafted_players_and_are_sorted(self) -> None:
        drafted = set(self.players.head(6)["player_id"])
        empty_roster = self.players.iloc[0:0]
        result = recommend_players(
            self.players,
            drafted,
            empty_roster,
            current_pick=12,
            lineup=LINEUP_PRESETS["Classic"],
            target_ids={self.players.iloc[20].player_id},
            limit=8,
        )
        self.assertEqual(len(result), 8)
        self.assertTrue(drafted.isdisjoint(result["player_id"]))
        self.assertTrue(result["fit_score"].is_monotonic_decreasing)
        self.assertTrue({"roster_need", "timing", "rationale"}.issubset(result.columns))

    def test_tracker_grid_has_round_and_team_shape(self) -> None:
        grid = tracker_grid(self.players, {}, team_count=10, rounds=12, user_slot=5)
        self.assertEqual(grid.shape, (12, 11))
        self.assertIn("My team (5)", grid.columns)

    def test_backup_validation_rejects_unknown_or_mismatched_data(self) -> None:
        valid_ids = set(self.players["player_id"])
        payload = {
            "version": 1,
            "dataset": "synthetic-draft-lab",
            "settings": {"league_size": 10, "rounds": 12},
            "picks": [{"pick": 1, "player_id": self.players.iloc[0].player_id}],
            "targets": [self.players.iloc[1].player_id],
        }
        board, targets = validate_backup_payload(payload, valid_ids, 10, 12)
        self.assertEqual(len(board), 1)
        self.assertEqual(len(targets), 1)

        invalid = {**payload, "picks": [{"pick": 1, "player_id": "UNKNOWN"}]}
        with self.assertRaises(ValueError):
            validate_backup_payload(invalid, valid_ids, 10, 12)

        with self.assertRaises(ValueError):
            validate_backup_payload({**payload, "notes": "unexpected"}, valid_ids, 10, 12)

        pick_with_extra_field = {
            **payload,
            "picks": [{"pick": 1, "player_id": self.players.iloc[0].player_id, "name": "extra"}],
        }
        with self.assertRaises(ValueError):
            validate_backup_payload(pick_with_extra_field, valid_ids, 10, 12)


if __name__ == "__main__":
    unittest.main()
