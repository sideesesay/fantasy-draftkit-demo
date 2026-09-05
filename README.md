# Synthetic Draft Lab

Synthetic Draft Lab is a public-repository version of a fantasy draft command
center. It preserves the interesting software work—interactive boards,
snake-draft state, roster-aware recommendations, comparisons, swap previews,
and projection ranges—while using only deterministic fictional fixtures.

Every bundled player name starts with `Demo `, every club starts with
`Demo Club `, and every record is marked synthetic. The application has no
network client, live feed, scraper, hosted model, analytics tracker, credential
requirement, or server-wide user-state file.

## Features

- Filterable fictional draft board with targets and drafted status.
- Transparent On the clock recommendations based on documented demo formulas.
- Side-by-side player comparison and fictional trend chart.
- Configurable 8-, 10-, or 12-team snake-draft tracker.
- Isolated mock-draft mode with synthetic opponent picks and adjustable variation.
- Session-only roster grading and one-for-one swap preview.
- Synthetic projection lab with low, central, and high ranges.
- Downloadable and strictly validated session backup using fictional IDs only.
- Automated checks for schema integrity and public-release boundaries.

## Run locally

Create a clean environment, install the two declared dependencies, and start
the app:

```powershell
python -m venv .venv
& '.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.venv\Scripts\python.exe' -m streamlit run streamlit_app.py
```

## Run the checks

```powershell
& '.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_*.py' -v
& '.venv\Scripts\python.exe' scripts\generate_synthetic_data.py
git diff --exit-code -- data
```

The first command validates the data, calculations, safety boundary, and every
Streamlit page. The second pair proves that the committed fixtures reproduce
from the documented seed.

## Synthetic data

`data/synthetic_players.csv` contains 192 fictional player profiles.
`data/synthetic_history.csv` contains four fictional periods per player. The
generator seed and row counts are recorded in `data/manifest.json`.

The generated `value_delta` convention is:

```text
value_delta = market_pick - model_rank
```

A positive value therefore means the fictional market pick is later than the
fictional model rank. All calculations are illustrative.

## Mock draft mode

The **Mock draft** page uses an independent, temporary practice board. Select
the practice league size, draft slot, round count, lineup, and opponent
variation, then choose **Auto-draft to my next pick**. Fictional opponents fill
only their open selections in snake order and stop before every pick belonging
to your mock roster.

Opponent choices are sampled from a small neighborhood around the best
available synthetic market pick: Low uses 3 spots, Medium uses 6, and High uses
10. Lower market picks remain more likely. Starting a fresh mock changes its
deterministic session seed and clears only the practice board; the manual
tracker remains unchanged.

Regenerate the fixtures with:

```powershell
python scripts\generate_synthetic_data.py
```

## Create the public repository

Copy only this directory into a new empty directory, then initialize a fresh
repository there. Do not publish it as a branch or fork of a private project
whose history contains restricted or personal material.

```powershell
git init
git add .
git status
git commit -m 'Initial synthetic public showcase'
```

Before the first commit, configure the author identity you want displayed
publicly. Review `git status` and make sure no environment, secret, output,
download, local-state, or private source file was copied into the new folder.

## Safety boundary

This cleanup reduces avoidable publication risk; it is not a legal opinion.
If you replace the fictional fixtures with outside material, obtain the
necessary rights and review the applicable license and terms before publishing
that material or deploying an application that redistributes it.

See `NOTICE.md`, `THIRD_PARTY_NOTICES.md`, and `data/README.md` for the precise
content boundary and schema.
