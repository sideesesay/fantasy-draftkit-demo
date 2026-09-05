from __future__ import annotations

import json
import random
import re
import unittest
from pathlib import Path

import pandas as pd

from draftlab.data import (
    HISTORY_COLUMNS,
    PLAYER_COLUMNS,
    validate_history,
    validate_players,
)
from scripts.generate_synthetic_data import SEED, build_history, build_players


ROOT = Path(__file__).resolve().parents[1]
PLAYER_PATH = ROOT / "data" / "synthetic_players.csv"
HISTORY_PATH = ROOT / "data" / "synthetic_history.csv"
MANIFEST_PATH = ROOT / "data" / "manifest.json"
PLAYER_OUTPUT_COLUMNS = [
    "player_id",
    "player_name",
    "club",
    "position",
    "model_rank",
    "market_pick",
    "value_delta",
    "tier",
    "projected_points",
    "projection_low",
    "projection_high",
    "upside",
    "floor",
    "risk",
    "profile",
    "is_synthetic",
]
HISTORY_OUTPUT_COLUMNS = [
    "player_id",
    "season_index",
    "season_label",
    "games",
    "points",
    "points_per_game",
    "opportunities_per_game",
    "is_synthetic",
]


class SyntheticDataIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw_players = pd.read_csv(PLAYER_PATH)
        cls.players = validate_players(cls.raw_players)
        cls.raw_history = pd.read_csv(HISTORY_PATH)
        cls.history = validate_history(cls.raw_history, set(cls.players["player_id"]))

    def test_player_schema_and_counts(self) -> None:
        self.assertEqual(set(self.raw_players.columns), PLAYER_COLUMNS)
        self.assertEqual(len(self.players), 192)
        self.assertEqual(
            self.players["position"].value_counts().to_dict(),
            {"WR": 72, "RB": 60, "TE": 36, "QB": 24},
        )
        self.assertTrue(self.players["player_id"].str.fullmatch(r"SYN-\d{3}").all())
        self.assertTrue(self.players["player_name"].str.startswith("Demo ").all())
        self.assertTrue(self.players["club"].str.startswith("Demo Club ").all())
        self.assertTrue(self.players["is_synthetic"].all())

    def test_player_math_and_ranges(self) -> None:
        self.assertEqual(self.players["model_rank"].tolist(), list(range(1, 193)))
        expected_value = self.players["market_pick"] - self.players["model_rank"]
        self.assertTrue((expected_value - self.players["value_delta"]).abs().le(0.01).all())
        self.assertTrue(self.players["market_pick"].between(1, 192).all())
        self.assertTrue(
            (self.players["projection_low"] <= self.players["projected_points"]).all()
        )
        self.assertTrue(
            (self.players["projected_points"] <= self.players["projection_high"]).all()
        )
        for column in ("upside", "floor", "risk"):
            self.assertTrue(self.players[column].between(1, 5).all())
            self.assertTrue((self.players[column] % 1 == 0).all())

    def test_history_schema_and_relationships(self) -> None:
        self.assertEqual(set(self.raw_history.columns), HISTORY_COLUMNS)
        self.assertEqual(len(self.history), 768)
        self.assertEqual(set(self.history["player_id"]), set(self.players["player_id"]))
        self.assertFalse(self.history.duplicated(["player_id", "season_index"]).any())
        self.assertTrue(self.history["games"].between(13, 17).all())
        self.assertFalse(self.history["season_label"].str.contains(r"\b20\d{2}\b").any())
        for _, group in self.history.groupby("player_id"):
            self.assertEqual(group["season_index"].tolist(), [-3, -2, -1, 0])
        calculated = self.history["points"] / self.history["games"]
        self.assertTrue((calculated - self.history["points_per_game"]).abs().le(0.02).all())

    def test_manifest_declares_the_generation_boundary(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest["seed"], 20260905)
        self.assertEqual(manifest["player_rows"], 192)
        self.assertEqual(manifest["history_rows"], 768)
        self.assertEqual(manifest["external_sources"], [])

    def test_committed_files_match_the_deterministic_generator(self) -> None:
        rng = random.Random(SEED)
        generated_players = build_players(rng)
        generated_history = build_history(generated_players, rng)
        expected_players = pd.DataFrame(generated_players)[PLAYER_OUTPUT_COLUMNS]
        expected_history = pd.DataFrame(generated_history)[HISTORY_OUTPUT_COLUMNS]
        pd.testing.assert_frame_equal(
            self.raw_players,
            expected_players,
            check_dtype=False,
            check_exact=False,
            atol=1e-9,
        )
        pd.testing.assert_frame_equal(
            self.raw_history,
            expected_history,
            check_dtype=False,
            check_exact=False,
            atol=1e-9,
        )


if __name__ == "__main__":
    unittest.main()
