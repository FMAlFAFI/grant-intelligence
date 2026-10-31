from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dashboard" / "streamlit_app.py"
REGISTER = ROOT / "results" / "register" / "grants_register.csv"
PAGES = ["glance", "projects", "project_file", "alerts", "portfolio", "priority_check", "drift"]


@pytest.mark.skipif(not REGISTER.exists(), reason="grant register not generated")
@pytest.mark.parametrize("page", PAGES)
def test_page_opens_without_an_exception(page):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.switch_page(f"views/{page}.py").run()
    assert not app.exception


@pytest.mark.skipif(not REGISTER.exists(), reason="grant register not generated")
def test_completed_and_all_groups_open_on_the_projects_page():
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.switch_page("views/projects.py").run()
    for group in ("Completed", "All"):
        app.button_group[0].set_value(group).run()
        assert not app.exception
