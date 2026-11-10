"""The review rubric, read from config/review_criteria.yaml and never defined in code."""
from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "review_criteria.yaml"


@lru_cache(maxsize=None)
def load_rubric(path=CONFIG_PATH):
    """Return the rubric as a dict of code lists, maxima, names and the gate overlap.

    Returns:
        form_codes: the 15 criteria printed on the form
        separate: the four methodology criteria (C to F) that a reviewer may merge into one mark
        combined: the code of that single mark
        comparable: the 12 criteria every review has, with C to F as the single mark
        maxima, names: by code, including the combined mark
        gate_overlap: initial assessment question -> rubric codes it overlaps
    """
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    criteria, combined = data["review_criteria"], data["combined_methodology"]
    maxima = {c["code"]: float(c["weight"]) for c in criteria}
    names = {c["code"]: c["name"] for c in criteria}
    maxima[combined["code"]] = sum(maxima[part] for part in combined["parts"])
    names[combined["code"]] = combined["name"]
    comparable = []
    for criterion in criteria:
        code = combined["code"] if criterion["code"] in combined["parts"] else criterion["code"]
        if code not in comparable:
            comparable.append(code)
    return {
        "form_codes": [c["code"] for c in criteria],
        "separate": list(combined["parts"]),
        "combined": combined["code"],
        "comparable": comparable,
        "maxima": maxima,
        "names": names,
        "gate_overlap": {gate: list(codes) for gate, codes in data["gate_overlap"].items()},
    }
