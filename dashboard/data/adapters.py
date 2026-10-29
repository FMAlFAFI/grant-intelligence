from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from dashboard.data.contracts import CONTRACTS, missing_columns
from dashboard.data.loaders import settings
from dashboard.settings import ROOT


@dataclass
class ModuleOutput:
    name: str
    owner: str
    ready: bool
    frame: pd.DataFrame
    missing: list = field(default_factory=list)


def empty_frame(name):
    return pd.DataFrame(columns=CONTRACTS[name])


def relative(path):
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_pending(module):
    if not module.file.exists():
        missing = [
            f"File {module.file.name} expected at {relative(module.file)}",
            f"Produced by {module.produced_by}",
            "Columns, one row per grant_id: " + ", ".join(CONTRACTS[module.name]),
        ]
        return ModuleOutput(module.name, module.owner, False, empty_frame(module.name), missing)
    frame = pd.read_csv(module.file, encoding="utf-8-sig")
    gaps = missing_columns(frame, module.name)
    if gaps:
        missing = [f"{module.file.name} exists but lacks columns: " + ", ".join(gaps)]
        return ModuleOutput(module.name, module.owner, False, empty_frame(module.name), missing)
    return ModuleOutput(module.name, module.owner, True, frame)


@st.cache_data
def load_drift():
    return read_pending(settings().pending["drift"])


@st.cache_data
def load_stalls():
    return read_pending(settings().pending["stalls"])
