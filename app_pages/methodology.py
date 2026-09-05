"""Explain the public build's synthetic provenance and safety boundaries."""

import json
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))

st.title("Methodology and public-safety boundary")
st.write(
    "This repository is a software demonstration. Its bundled records are created from scratch by "
    "a deterministic generator and are deliberately unsuitable for real-world draft decisions."
)

with st.container(border=True):
    st.subheader("Synthetic provenance")
    st.json(manifest, expanded=True)

with st.container(border=True):
    st.subheader("Illustrative model")
    st.markdown(
        """
        1. Position-specific fictional baselines and slopes create a varied player pool.
        2. A seeded pseudo-random generator adds bounded variation.
        3. Model rank orders the resulting fictional talent scores.
        4. Market pick adds independent fictional drift; `value = market pick − model rank`.
        5. Recommendation fit combines rank, value, pick timing, upside, risk, roster openings, and targets.
        6. Mock opponents sample from a bounded synthetic market-pick neighborhood and stop before the user's snake pick.
        """
    )

with st.container(border=True):
    st.subheader("Intentionally absent")
    st.markdown(
        """
        - Real athlete or club identities, rankings, statistics, projections, news, and images.
        - Third-party feeds, scrapers, downloaded source files, and generated reports based on them.
        - Hosted language-model calls, analytics trackers, credentials, and server-wide user storage.
        """
    )

st.info(
    "If you replace the fictional fixtures, confirm that you have the necessary rights and review "
    "the new source's license and terms before publishing the replacement data.",
    icon=":material/info:",
)
