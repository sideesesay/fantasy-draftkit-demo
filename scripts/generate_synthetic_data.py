"""Generate deterministic, fictional data for the public showcase.

This script intentionally does not read files, services, rankings, statistics,
names, or identifiers from any external source.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path


SEED = 20260905
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PLAYER_PATH = DATA_DIR / "synthetic_players.csv"
HISTORY_PATH = DATA_DIR / "synthetic_history.csv"
MANIFEST_PATH = DATA_DIR / "manifest.json"

POSITION_COUNTS = {"QB": 24, "RB": 60, "WR": 72, "TE": 36}
CLUBS = [
    "Demo Club Aurora",
    "Demo Club Beacon",
    "Demo Club Comet",
    "Demo Club Drift",
    "Demo Club Ember",
    "Demo Club Flux",
    "Demo Club Grove",
    "Demo Club Harbor",
    "Demo Club Ion",
    "Demo Club Juniper",
    "Demo Club Kestrel",
    "Demo Club Lunar",
]
CALLSIGNS = [
    "Axiom",
    "Beryl",
    "Cipher",
    "Delta",
    "Echo",
    "Fable",
    "Garnet",
    "Halo",
    "Indigo",
    "Jasper",
    "Kite",
    "Lumen",
    "Mosaic",
    "Nova",
    "Orbit",
    "Prism",
    "Quartz",
    "Relay",
    "Solstice",
    "Tempo",
    "Umber",
    "Vector",
    "Willow",
    "Zenith",
]
PROFILE_NOTES = {
    "steady": "Stable illustrative workload with a narrow demo range.",
    "upside": "High-variance illustrative profile with extra demo ceiling.",
    "balanced": "Balanced fictional projection across the demo inputs.",
    "development": "Later-stage fictional profile intended for depth testing.",
}


def bounded_int(value: float, low: int = 1, high: int = 5) -> int:
    return max(low, min(high, int(round(value))))


def build_players(rng: random.Random) -> list[dict[str, object]]:
    slopes = {"QB": 2.55, "RB": 1.18, "WR": 1.02, "TE": 1.72}
    premiums = {"QB": -2.0, "RB": 4.0, "WR": 3.5, "TE": -1.0}
    point_bases = {"QB": 365.0, "RB": 305.0, "WR": 295.0, "TE": 245.0}
    point_slopes = {"QB": 7.0, "RB": 3.25, "WR": 2.55, "TE": 4.1}
    raw_rows: list[dict[str, object]] = []
    global_index = 0

    for position, count in POSITION_COUNTS.items():
        for position_index in range(1, count + 1):
            global_index += 1
            callsign = CALLSIGNS[(global_index * 5 + position_index) % len(CALLSIGNS)]
            talent_score = (
                101.0
                + premiums[position]
                - position_index * slopes[position]
                + rng.uniform(-2.4, 2.4)
            )
            risk = bounded_int(rng.gauss(2.8 + position_index / max(count, 1), 1.0))
            upside = bounded_int(rng.gauss(3.5 - position_index / (count * 2), 0.9))
            floor = bounded_int(6.0 - risk + rng.uniform(-0.7, 0.7))
            projected = max(
                58.0,
                point_bases[position]
                - (position_index - 1) * point_slopes[position]
                + rng.uniform(-11.0, 11.0),
            )
            if risk >= 4 and upside >= 4:
                profile_key = "upside"
            elif risk <= 2:
                profile_key = "steady"
            elif position_index > count * 0.72:
                profile_key = "development"
            else:
                profile_key = "balanced"
            raw_rows.append(
                {
                    "player_id": f"SYN-{global_index:03d}",
                    "player_name": f"Demo {callsign} {position}-{position_index:02d}",
                    "club": CLUBS[(global_index + position_index) % len(CLUBS)],
                    "position": position,
                    "position_index": position_index,
                    "talent_score": talent_score,
                    "projected_points": projected,
                    "upside": upside,
                    "floor": floor,
                    "risk": risk,
                    "profile": PROFILE_NOTES[profile_key],
                }
            )

    raw_rows.sort(key=lambda row: (-float(row["talent_score"]), str(row["player_id"])))
    total = len(raw_rows)
    for model_rank, row in enumerate(raw_rows, start=1):
        position_drift = {"QB": 3.0, "RB": -1.5, "WR": 0.0, "TE": 4.5}[str(row["position"])]
        market_pick = max(
            1.0,
            min(float(total), model_rank + position_drift + rng.gauss(0.0, 10.5)),
        )
        if model_rank <= 12:
            tier = "Cornerstone"
        elif model_rank <= 36:
            tier = "Foundation"
        elif model_rank <= 72:
            tier = "Starter"
        elif model_rank <= 120:
            tier = "Depth"
        else:
            tier = "Development"
        projected = float(row["projected_points"])
        risk = int(row["risk"])
        upside = int(row["upside"])
        row.update(
            {
                "model_rank": model_rank,
                "market_pick": round(market_pick, 1),
                "value_delta": round(market_pick - model_rank, 1),
                "tier": tier,
                "projected_points": round(projected, 1),
                "projection_low": round(projected * (0.75 - risk * 0.015), 1),
                "projection_high": round(projected * (1.11 + upside * 0.025), 1),
                "is_synthetic": True,
            }
        )
    return raw_rows


def build_history(players: list[dict[str, object]], rng: random.Random) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    opportunity_bases = {"QB": 36.0, "RB": 17.0, "WR": 9.5, "TE": 6.8}
    for player in players:
        central = float(player["projected_points"])
        position = str(player["position"])
        direction = rng.uniform(-0.025, 0.06)
        for season_index in range(-3, 1):
            relative_year = season_index + 1
            season_points = max(
                30.0,
                central * (1.0 + direction * relative_year) + rng.uniform(-22.0, 22.0),
            )
            games = rng.randint(13, 17)
            opportunities = max(
                2.0,
                opportunity_bases[position]
                + rng.uniform(-2.5, 2.5)
                - max(0, int(player["position_index"]) - 20) * 0.04,
            )
            rows.append(
                {
                    "player_id": player["player_id"],
                    "season_index": season_index,
                    "season_label": "Current demo" if season_index == 0 else f"Demo year {season_index}",
                    "games": games,
                    "points": round(season_points, 1),
                    "points_per_game": round(season_points / games, 2),
                    "opportunities_per_game": round(opportunities, 2),
                    "is_synthetic": True,
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    players = build_players(rng)
    history = build_history(players, rng)
    write_csv(
        PLAYER_PATH,
        players,
        [
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
        ],
    )
    write_csv(
        HISTORY_PATH,
        history,
        [
            "player_id",
            "season_index",
            "season_label",
            "games",
            "points",
            "points_per_game",
            "opportunities_per_game",
            "is_synthetic",
        ],
    )
    manifest = {
        "dataset": "Synthetic Draft Lab fictional demo data",
        "seed": SEED,
        "player_rows": len(players),
        "history_rows": len(history),
        "external_sources": [],
        "identity_rule": "Every player name starts with 'Demo ' and every club starts with 'Demo Club '.",
        "generator": "scripts/generate_synthetic_data.py",
        "license_scope": "Original fictional demo data distributed with this project.",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
