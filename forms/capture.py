"""Minimal capture forms for the four institutional records (brief, Stage 8).

Each saved record is one row of a CSV under the capture folder. Names are replaced by pseudonym codes
before anything is written, with the same mapping the pseudonymiser uses (kept outside the
repository), and every free-text field is stored with its language. The forms only capture data: they
do not score, route or decide anything.
"""
import csv
from datetime import datetime

from app.ingestion.language_tagger import tag
from app.ingestion.pseudonymiser import REVIEWER, RESEARCHER, Mapping, check_outside_repo
from config.config import get_config

PROPOSAL, ASSESSMENT, REVIEW, PROGRESS = "proposals", "assessments", "reviews", "progress_reports"
GATE_QUESTIONS = {
    "topic": "Is the title relevant, clear, and scientifically sound?",
    "team": "Do the researchers have the necessary qualifications and experience?",
    "budget": "Is the budget reasonable and justified?",
    "methodology": "Is the research plan, including data collection and analysis, appropriate?",
}
METHODOLOGY_SECTIONS = ["Population and sampling", "Data collection", "Techniques and procedures",
                        "Statistical analysis", "Ethical considerations"]


def pseudonym(role, name, source):
    """Return the pseudonym code for a name and store the link in the mapping outside the repository."""
    path = get_config().PSEUDONYM_MAP_PATH
    check_outside_repo(path)
    mapping = Mapping(path)
    code = mapping.code(role, name.strip(), source=source)
    mapping.save()
    return code


def with_languages(record, text_fields):
    """Add a <field>_lang column for every free-text field of a record."""
    return {**record, **{f"{field}_lang": tag(str(record.get(field, ""))) for field in text_fields}}


def save_record(kind, record):
    """Append one record to the CSV of its form type and return the file it was written to."""
    folder = get_config().CAPTURE_DIR
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{kind}.csv"
    record = {**record, "captured_at": datetime.now().isoformat(timespec="seconds")}
    is_new = not path.exists()
    if not is_new:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            header = next(csv.reader(handle))
        if header != list(record):
            raise ValueError(f"{path.name} has other columns than this form writes; move it aside and save again.")
    with path.open("a", encoding="utf-8-sig" if is_new else "utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(record))
        if is_new:
            writer.writeheader()
        writer.writerow(record)
    return path


def review_record(proposal_number, reviewer_name, scores, comments, combined, classification, general_comment, rubric):
    """Build the row for one review: scores for the form variant used, their total and the comments."""
    codes = rubric["comparable"] if combined else rubric["form_codes"]
    record = {"proposal_number": proposal_number.strip(),
              "reviewer": pseudonym(REVIEWER, reviewer_name, f"captured/{REVIEW}"),
              "form_variant": "combined" if combined else "standard"}
    for code in rubric["form_codes"] + [rubric["combined"]]:
        record[code] = scores.get(code) if code in codes else ""
        record[f"{code}_comment"] = comments.get(code, "") if code in codes else ""
    record["total"] = sum(scores[code] for code in codes)
    record.update(classification=classification, general_comment=general_comment.strip())
    return with_languages(record, ["general_comment"] + [f"{code}_comment" for code in codes])


def render_proposal_form(st, priorities):
    with st.form("capture_proposal", clear_on_submit=True):
        left, right = st.columns(2)
        with left:
            round_number = st.text_input("Round number *", placeholder="ROUND-2026-01")
            number = st.text_input("Proposal number *")
            priority = st.selectbox("Research priority *", [f"{p.name_en} / {p.name_ar}" for p in priorities])
            project_type = st.selectbox("Project type *", ["small", "medium", "large"])
        with right:
            title = st.text_input("Title *")
            investigator = st.text_input("Principal investigator *", help="Stored as a pseudonym code, never as a name.")
            budget = st.number_input("Suggested budget (SAR)", min_value=0.0, step=1000.0)
            duration = st.number_input("Duration (months)", min_value=1, max_value=60, value=12)
        abstract = st.text_area("Abstract (200 to 250 words) *")
        keywords = st.text_input("Keywords")
        background = st.text_area("Background and justification")
        methodology = {name: st.text_area(f"Methodology: {name}") for name in METHODOLOGY_SECTIONS}
        expected = st.text_area("Expected publications and patents")
        st.caption("Team members, timetable, itemised budget and earlier publications are tables on the Word form. "
                   "This minimal form does not capture them.")
        if st.form_submit_button("Save proposal"):
            if not all(value.strip() for value in (round_number, number, title, investigator, abstract)):
                st.error("Fill in every field marked with *.")
                return
            record = {"round_number": round_number.strip(), "proposal_number": number.strip(),
                      "research_priority": priority.split(" / ")[0], "project_type": project_type,
                      "title": title.strip(),
                      "principal_investigator": pseudonym(RESEARCHER, investigator, f"captured/{PROPOSAL}"),
                      "suggested_budget": budget, "duration_months": duration, "abstract": abstract.strip(),
                      "keywords": keywords.strip(), "background": background.strip(),
                      **{f"methodology_{name.lower().replace(' ', '_')}": text.strip()
                         for name, text in methodology.items()},
                      "expected_publications": expected.strip()}
            text_fields = [field for field in record if field in ("title", "abstract", "keywords", "background",
                                                                  "expected_publications") or field.startswith("methodology_")]
            path = save_record(PROPOSAL, with_languages(record, text_fields))
            st.success(f"Saved {number.strip()} to {path.name}. Investigator stored as {record['principal_investigator']}.")


def render_assessment_form(st):
    with st.form("capture_assessment", clear_on_submit=True):
        number = st.text_input("Proposal number *")
        answers, notes = {}, {}
        for key, question in GATE_QUESTIONS.items():
            left, right = st.columns([1, 2])
            with left:
                answers[key] = st.radio(question, ["yes", "no"], horizontal=True, key=f"gate_{key}")
            with right:
                notes[key] = st.text_input("Notes", key=f"gate_note_{key}")
        recommendation = st.selectbox("Recommendation *", ["approve", "revise", "reject"])
        if st.form_submit_button("Save initial assessment"):
            if not number.strip():
                st.error("Fill in the proposal number.")
                return
            record = {"proposal_number": number.strip(),
                      **{f"gate_{key}": answers[key] for key in GATE_QUESTIONS},
                      **{f"gate_{key}_notes": notes[key].strip() for key in GATE_QUESTIONS},
                      "recommendation": recommendation}
            path = save_record(ASSESSMENT, with_languages(record, [f"gate_{key}_notes" for key in GATE_QUESTIONS]))
            st.success(f"Saved the assessment of {number.strip()} to {path.name}.")


def render_review_form(st, rubric):
    combined = st.radio("Methodology criteria C to F", ["four separate marks out of 3", "one mark out of 12 (C to F do not apply)"],
                        horizontal=True) != "four separate marks out of 3"
    codes = rubric["comparable"] if combined else rubric["form_codes"]
    with st.form("capture_review", clear_on_submit=True):
        number = st.text_input("Proposal number *")
        reviewer = st.text_input("Reviewer *", help="Stored as a pseudonym code, never as a name.")
        scores, comments = {}, {}
        for code in codes:
            maximum = int(rubric["maxima"][code])
            left, right = st.columns([1, 2])
            with left:
                scores[code] = st.number_input(f"{code} {rubric['names'][code]} (max {maximum})", min_value=0,
                                               max_value=maximum, value=0, key=f"score_{code}")
            with right:
                comments[code] = st.text_input("Comment", key=f"comment_{code}")
        classification = st.radio("Category of the proposal", ["basic", "applied"], horizontal=True)
        general = st.text_area("Other comments to the research team")
        if st.form_submit_button("Save review"):
            if not number.strip() or not reviewer.strip():
                st.error("Fill in the proposal number and the reviewer.")
                return
            record = review_record(number, reviewer, scores, comments, combined, classification, general, rubric)
            path = save_record(REVIEW, record)
            st.success(f"Saved the review of {number.strip()} to {path.name}: total {record['total']} of 100, "
                       f"reviewer stored as {record['reviewer']}.")


def render_progress_form(st, stages):
    with st.form("capture_progress", clear_on_submit=True):
        left, right = st.columns(2)
        with left:
            number = st.text_input("Project number *")
            quarter = st.number_input("Report number (quarter)", min_value=1, max_value=12, value=1)
            report_date = st.date_input("Report date")
        with right:
            spent = st.number_input("Budget spent (SAR)", min_value=0.0, step=1000.0)
            remaining = st.number_input("Remaining amount (SAR)", min_value=0.0, step=1000.0)
            approval = st.text_input("Ethical approval number")
        percentages = {stage: st.slider(f"{stage} (%)", 0, 100, 0, key=f"stage_{index}")
                       for index, stage in enumerate(stages)}
        publications = st.text_area("Self-reported publications", help="One per line: title; journal; manuscript status")
        if st.form_submit_button("Save progress report"):
            if not number.strip():
                st.error("Fill in the project number.")
                return
            record = {"project_number": number.strip(), "quarter": quarter, "report_date": report_date.isoformat(),
                      **{f"stage{index}_percent": value for index, value in enumerate(percentages.values(), start=1)},
                      "budget_spent": spent, "remaining_amount": remaining, "ethical_approval_number": approval.strip(),
                      "self_reported_publications": " | ".join(line.strip() for line in publications.splitlines() if line.strip())}
            path = save_record(PROGRESS, with_languages(record, ["self_reported_publications"]))
            st.success(f"Saved report {quarter} of {number.strip()} to {path.name}.")
