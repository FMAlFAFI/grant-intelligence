import pandas as pd
import streamlit as st

from dashboard.data.contracts import check
from dashboard.settings import load_settings

PRIORITY_ORDER = [
    "National Security",
    "Cybercrimes and Financial Crimes",
    "AI and Emerging Technologies",
    "Transnational Security Threats",
    "Narcotics and Psychotropic Substances",
]


class MissingOutput(FileNotFoundError):
    def __init__(self, path, command):
        self.path = path
        self.command = command
        super().__init__(f"{path} not found, run: {command}")


def read_csv(path, command, contract=None, **options):
    if not path.exists():
        raise MissingOutput(path, command)
    frame = pd.read_csv(path, encoding="utf-8-sig", **options)
    return check(frame, contract) if contract else frame


@st.cache_resource
def settings():
    return load_settings()


@st.cache_data
def load_register():
    return read_csv(settings().register, "python -m app.ingestion.grant_register", "register")


@st.cache_data
def load_progress_history():
    return read_csv(settings().progress_history, "python -m app.ingestion.grant_register", "progress_history")


@st.cache_data
def load_proposals():
    folder = settings().portfolio_dir
    return read_csv(folder / "proposals.csv", "python -m app.classification.portfolio_map", "proposals")


@st.cache_data
def load_priority_by_round():
    folder = settings().portfolio_dir
    table = read_csv(folder / "priority_by_round.csv", "python -m app.classification.portfolio_map", index_col=0)
    return table.drop(index="Total", errors="ignore").drop(columns="Total", errors="ignore")


def run_command(method, dataset):
    command = f"python -m app.classification.evaluate_priorities --method {method}"
    if dataset == "hard":
        command += (" --proposals data/synthetic/hard/raw/proposals"
                    " --truth data/synthetic/hard/ground_truth/grants.csv")
    return command


@st.cache_data
def load_metrics(method, dataset):
    folder = settings().priority_dir(method, dataset)
    return read_csv(folder / "metrics.csv", run_command(method, dataset), "metrics")


@st.cache_data
def load_predictions(method, dataset):
    folder = settings().priority_dir(method, dataset)
    return read_csv(folder / "predictions_with_truth.csv", run_command(method, dataset), "predictions")


@st.cache_data
def load_claim_disagreements(method, dataset):
    folder = settings().priority_dir(method, dataset)
    return read_csv(folder / "claim_disagreements.csv", run_command(method, dataset), "claim_disagreements")


def macro_f1(metrics, subset="all"):
    rows = metrics[metrics["subset"] == subset]
    return float(rows["f1"].mean()) if len(rows) else None
