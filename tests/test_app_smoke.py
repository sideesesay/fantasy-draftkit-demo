from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    "app_pages/board.py",
    "app_pages/on_clock.py",
    "app_pages/compare.py",
    "app_pages/tracker.py",
    "app_pages/mock_draft.py",
    "app_pages/roster.py",
    "app_pages/projections.py",
    "app_pages/methodology.py",
]


class AppSmokeTests(unittest.TestCase):
    def test_every_page_renders_without_exception(self) -> None:
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=15).run()
        self.assertEqual(list(app.exception), [])

        for page in PAGES:
            with self.subTest(page=page):
                app.switch_page(page).run(timeout=15)
                self.assertEqual(list(app.exception), [])

    def test_mock_draft_advances_opponents_without_changing_manual_board(self) -> None:
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=15).run()
        app.session_state["draft_board"] = {1: "SYN-192"}
        app.switch_page("app_pages/mock_draft.py").run(timeout=15)

        app.button(key="mock_auto_draft").click().run(timeout=15)
        self.assertEqual(set(app.session_state["mock_draft_board"]), {1, 2, 3, 4})
        self.assertEqual(app.session_state["draft_board"], {1: "SYN-192"})

        app.button(key="mock_make_pick").click().run(timeout=15)
        self.assertIn(5, app.session_state["mock_draft_board"])
        self.assertEqual(app.session_state["draft_board"], {1: "SYN-192"})


if __name__ == "__main__":
    unittest.main()
