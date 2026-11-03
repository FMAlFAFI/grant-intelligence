import re
from collections import defaultdict
from pathlib import Path

import streamlit as st

from dashboard.data.loaders import settings
from app.ingestion.text_extractor import extract_lines

GRANT_ID = re.compile(r"NAUSS-\d{2}-R\d{2}-\d{3}")
FORM_KINDS = {
    "proposals": "Proposal",
    "assessments": "Initial assessment",
    "reviews": "Reviewer form",
    "progress_reports": "Quarterly progress report",
    "final_reports": "Final report",
}
PRIVATE_KINDS = {"reviews"}


def index_sources(raw_dir):
    index = defaultdict(list)
    for folder, label in FORM_KINDS.items():
        for path in sorted(Path(raw_dir, folder).glob("*.docx")):
            match = GRANT_ID.search(path.name)
            if match:
                index[match.group()].append({
                    "kind": folder,
                    "label": label,
                    "path": path,
                    "private": folder in PRIVATE_KINDS,
                })
    return dict(index)


@st.cache_data
def source_index():
    return index_sources(settings().raw_dir)


def sources_for(grant_id):
    return source_index().get(grant_id, [])


@st.cache_data
def document_lines(path):
    return extract_lines(path)
