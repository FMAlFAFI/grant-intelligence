CONTRACTS = {
    "register": [
        "grant_id", "round", "year", "round_label", "title", "lang", "type", "college", "department", "budget", "planned_months",
        "assessment", "n_reviews", "mean_review_total", "funded", "reports_received", "reports_planned",
        "current_stage", "overall_progress", "budget_spent", "final_report", "extended", "status",
    ],
    "progress_history": ["grant_id", "quarter", "budget_spent", "overall_progress", "current_stage"],
    "proposals": ["grant_id", "round", "type", "college", "department", "lang", "claimed_priority", "predicted_priority", "funded"],
    "metrics": ["priority", "support", "precision", "recall", "f1", "subset"],
    "predictions": ["grant_id", "lang", "claimed_priority", "predicted_priority", "content_priority"],
    "claim_disagreements": ["grant_id", "lang", "claimed_priority", "predicted_priority", "margin"],
    "trajectories": [
        "project_number", "quarter", "literature_review", "instrument_design", "ethics_approval",
        "data_collection", "data_analysis", "writing_results", "paper_submission", "final_report",
    ],
    "timetables": ["proposal_number", "task", "from_month", "to_month"],
    "drift": ["grant_id", "similarity", "threshold", "drift_flag", "n_papers"],
    "stalls": [
        "grant_id", "stage", "start_quarter", "alert_quarter", "end_quarter", "reports", "from_pct", "to_pct", "ongoing",
    ],
    "slip": [
        "grant_id", "stage", "planned_to_month", "planned_quarter", "done_quarter", "last_quarter", "slip_quarters",
        "status",
    ],
    "extensions": ["grant_id", "extended", "planned_months", "reports_used", "flag_quarter", "lead_months"],
}


class ContractError(ValueError):
    def __init__(self, name, missing):
        self.name = name
        self.missing = missing
        super().__init__(f"{name} is missing columns: {', '.join(missing)}")


def missing_columns(frame, name):
    return [column for column in CONTRACTS[name] if column not in frame.columns]


def check(frame, name):
    missing = missing_columns(frame, name)
    if missing:
        raise ContractError(name, missing)
    return frame
