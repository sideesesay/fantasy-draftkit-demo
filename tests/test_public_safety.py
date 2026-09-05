from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".csv", ".json", ".toml", ".txt", ".md", ".yml", ".yaml"}
PROVIDER_TERMS = [
    "fantasy" + "pros",
    "beat" + "adp",
    "sleep" + "er",
    "esp" + "n",
    "under" + "dog",
    "sports" + "-reference",
    "pro-football" + "-reference",
    "stat" + "head",
]
NETWORK_IMPORTS = [
    "request" + "s",
    "http" + "x",
    "aio" + "http",
    "urllib" + ".request",
    "sock" + "et",
    "open" + "ai",
    "google" + "-genai",
]
PRIVATE_MODULES = [
    "league" + "_digest",
    "draft" + "_llm",
    "historical" + "_projections",
    "source" + "_extracts",
]


class PublicSafetyTests(unittest.TestCase):
    def iter_text_files(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
                continue
            if path.suffix.lower() in TEXT_SUFFIXES or path.name == "LICENSE":
                yield path

    def test_no_provider_content_network_code_or_private_paths(self) -> None:
        rules = {
            "provider-specific term": re.compile("|".join(map(re.escape, PROVIDER_TERMS)), re.I),
            "runtime URL": re.compile("http" + r"s?://|" + "www" + r"\.", re.I),
            "local user path": re.compile(
                r"C:\\" + "Users" + r"\\|/" + "Users" + r"/|/" + "home" + r"/",
                re.I,
            ),
            "network dependency": re.compile(
                r"\b(?:" + "|".join(map(re.escape, NETWORK_IMPORTS)) + r")\b", re.I
            ),
            "private module": re.compile("|".join(map(re.escape, PRIVATE_MODULES)), re.I),
            "secrets access": re.compile(r"st\.secrets|os\.(?:getenv|environ)", re.I),
            "credential token": re.compile(
                r"AIza[0-9A-Za-z_-]{20,}|AKIA[0-9A-Z]{16}|ghp_[0-9A-Za-z]{20,}|"
                r"xox[baprs]-[0-9A-Za-z-]{10,}|BEGIN [A-Z ]*PRIVATE KEY",
                re.I,
            ),
        }
        failures: list[str] = []
        for path in self.iter_text_files():
            text = path.read_text(encoding="utf-8")
            for label, pattern in rules.items():
                if pattern.search(text):
                    failures.append(f"{path.relative_to(ROOT)}: {label}")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_forbidden_private_artifacts_are_absent(self) -> None:
        forbidden = [
            ROOT / ".env",
            ROOT / ".streamlit" / "secrets.toml",
            ROOT / ".draft_command_center_state.json",
            ROOT / ("source" + "_extracts"),
            ROOT / "outputs",
        ]
        self.assertEqual([str(path) for path in forbidden if path.exists()], [])


if __name__ == "__main__":
    unittest.main()
