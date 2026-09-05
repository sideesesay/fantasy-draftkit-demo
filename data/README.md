# Synthetic dataset schema

Both CSV files are generated locally from the fixed seed in
`scripts/generate_synthetic_data.py`. The generator has no read path and no
external dependency.

## `synthetic_players.csv`

| Field | Meaning |
| --- | --- |
| `player_id` | Stable fictional identifier matching `SYN-###`. |
| `player_name` | Fictional display name beginning with `Demo `. |
| `club` | Fictional club beginning with `Demo Club `. |
| `position` | One of `QB`, `RB`, `WR`, or `TE`. |
| `model_rank` | Unique contiguous demo rank. |
| `market_pick` | Independently perturbed fictional selection point. |
| `value_delta` | `market_pick - model_rank`. |
| `tier` | Generated grouping for the interface. |
| `projected_points` | Central illustrative projection. |
| `projection_low` | Lower illustrative bound. |
| `projection_high` | Upper illustrative bound. |
| `upside`, `floor`, `risk` | Bounded fictional scores from 1 through 5. |
| `profile` | Generated generic demo description. |
| `is_synthetic` | Required truth marker. |

## `synthetic_history.csv`

Each player has exactly four generated periods, indexed from `-3` through `0`.
The points, per-game values, and opportunity values are illustrative fixtures.
They do not represent a calendar year, real competition, person, or club.
