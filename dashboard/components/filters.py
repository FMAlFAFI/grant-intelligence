import re
from dataclasses import dataclass

import streamlit as st

GRANT_ID = re.compile(r"NAUSS-(\d{2})-R\d{2}-\d{3}")


def grant_year(grant_id):
    match = GRANT_ID.search(str(grant_id))
    return 2000 + int(match.group(1)) if match else None


@dataclass
class Filters:
    grant_ids: set
    total: int

    @property
    def active(self):
        return len(self.grant_ids) < self.total

    def apply(self, frame, column="grant_id"):
        return frame[frame[column].isin(self.grant_ids)]


def choose(label, options, key, format_func=str):
    return st.sidebar.multiselect(label, options, default=[], key=key, format_func=format_func,
                                  placeholder="All")


def sidebar_filters(register):
    st.sidebar.header("Filters")
    years = choose("Funding round", sorted(register["year"].unique()), "filter_year",
                   lambda year: f"Round {year - 2022} ({year})")
    colleges = choose("College", sorted(register["college"].unique()), "filter_college")

    kept = register
    for column, values in (("year", years), ("college", colleges)):
        if values:
            kept = kept[kept[column].isin(values)]
    filters = Filters(set(kept["grant_id"]), len(register))
    st.sidebar.caption(f"Showing {len(filters.grant_ids)} of {filters.total} grants")
    return filters
