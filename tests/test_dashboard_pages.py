from codecs import register
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dashboard" / "streamlit_app.py"
REGISTER = ROOT / "results" / "register" / "grants_register.csv"
TRUTH = ROOT / "data" / "synthetic" / "ground_truth" / "grants.csv"
PAGES = ["glance", "projects", "project_file", "alerts", "portfolio", "priority_check", "drift"]


@pytest.mark.skipif(not REGISTER.exists(), reason="grant register not generated")
@pytest.mark.parametrize("page", PAGES)
def test_page_opens_without_an_exception(page):
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.switch_page(f"views/{page}.py").run()
    assert not app.exception


@pytest.mark.skipif(not REGISTER.exists(), reason="grant register not generated")
def test_projects_lists_every_proposal_by_default_and_filters_by_status():
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.switch_page("views/projects.py").run()
    assert len(app.dataframe[0].value) == len(pd.read_csv(REGISTER, encoding="utf-8-sig"))
    app.multiselect(key="projects_status").set_value(["Running"]).run()
    assert not app.exception
    assert set(app.dataframe[0].value["status"]) == {"Running"}


@pytest.mark.skipif(not REGISTER.exists(), reason="grant register not generated")
def test_dashboard_numbers_match_the_answer_key():
    register = pd.read_csv(REGISTER, encoding="utf-8-sig").set_index("grant_id")
    truth = pd.read_csv(TRUTH, encoding="utf-8-sig").set_index("grant_id")
    # Ensure we processed some grants (greater than 0)
    assert len(register) > 0
    # Ensure every grant in the dashboard exists in the original truth data
    for grant_id in register.index:
        assert grant_id in truth.index
    funded_accuracy = (register["funded"] == truth["funded"].reindex(register.index)).mean()
    assert funded_accuracy > 0.85
    final_report_accuracy = (register["final_report"] == truth["completed"].fillna(0).reindex(register.index)).mean()
    assert final_report_accuracy > 0.85
    extended_accuracy = (register["extended"] == truth["extended"].fillna(0).reindex(register.index)).mean()
    assert extended_accuracy > 0.85
