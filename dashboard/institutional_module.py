import os
import datetime
import streamlit as st
import pandas as pd

@st.cache_resource(show_spinner="Loading Qwen Embedding & Evaluation Model...")
def get_cached_model_instance(model_loader_fn, *args, **kwargs):
    """
    Loads and caches heavy LLM/embedding resources across the session.
    Enforces the 'No Silent Fallback' policy by raising explicit exceptions on failure.
    """
    try:
        model = model_loader_fn(*args, **kwargs)
        if model is None:
            raise ValueError("Model loader returned None.")
        return model
    except Exception as e:
        st.error(f"Critical System Error: Model initialization failed ({e}).")
        raise RuntimeError(f"No Silent Fallback Policy Enforced: {e}") from e


@st.cache_data(show_spinner="Evaluating proposal & computing embeddings (Cached)...")
def cached_model_inference(_inference_fn, payload_text: str):
    """
    Caches deterministic model outputs and vector embeddings based on input payload.
    Prevents redundant model calls and blocks silent fallback behavior.
    """
    if not payload_text or not payload_text.strip():
        raise ValueError("Inference payload cannot be empty.")
    try:
        result = _inference_fn(payload_text)
        if result is None:
            raise RuntimeError("Empty response received from model call.")
        return result
    except Exception as e:
        st.error(f"Model Inference Failure: {e}")
        raise RuntimeError(f"Silent fallback blocked during model call: {e}") from e


def render_capture_form(dataset_path: str = "data/captured_proposals.csv"):
    """
    Renders the institutional proposal capture form inside the Streamlit UI
    and appends validated records directly to the dataset.
    """
    st.subheader("Institutional Grant Proposal Capture Form")
    st.caption("Standardized Data Entry Interface - Appends directly to the institutional portfolio dataset.")

    with st.form(key="institutional_capture_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            prop_id = st.text_input("Proposal ID *", placeholder="e.g., GRANT-2026-089")
            title = st.text_input("Proposal Title *")
            pi_name = st.text_input("Principal Investigator (PI) *")
        with col2:
            department = st.selectbox(
                "Research Domain *",
                ["Artificial Intelligence", "Cybersecurity", "Data Science", "Telecommunications"]
            )
            budget = st.number_input(
                "Requested Budget (SAR) *",
                min_value=10000.0,
                max_value=5000000.0,
                value=150000.0,
                step=5000.0
            )
            prior_pubs = st.number_input(
                "PI Prior Publications Count *",
                min_value=0,
                max_value=200,
                value=5,
                step=1
            )

        abstract = st.text_area("Proposal Abstract & Technical Summary *", height=120)

        st.markdown("**Institutional Review Criteria Assessment (Scale: 1 = Poor to 5 = Excellent)**")
        criteria_scores = {}
        grid_cols = st.columns(4)
        for i in range(1, 15):
            with grid_cols[(i - 1) % 4]:
                criteria_scores[f"criterion_{i}"] = st.slider(
                    f"Criterion {i}",
                    min_value=1.0,
                    max_value=5.0,
                    value=3.0,
                    step=0.5
                )

        submitted = st.form_submit_button("Validate & Save Proposal")

        if submitted:
            if not (prop_id.strip() and title.strip() and pi_name.strip() and abstract.strip()):
                st.error("Validation Error: All starred (*) institutional fields are mandatory.")
                return

            new_record = {
                "proposal_id": prop_id.strip(),
                "title": title.strip(),
                "pi_name": pi_name.strip(),
                "department": department,
                "budget": budget,
                "prior_publications": prior_pubs,
                "abstract": abstract.strip(),
                "submission_timestamp": datetime.datetime.now().isoformat(),
                **criteria_scores,
                "is_successful": int(sum(criteria_scores.values()) / 14.0 >= 3.5)
            }

            df_new = pd.DataFrame([new_record])
            if os.path.exists(dataset_path):
                df_new.to_csv(dataset_path, mode="a", header=False, index=False)
            else:
                df_new.to_csv(dataset_path, mode="w", header=True, index=False)

            st.success(f"Proposal '{prop_id}' verified and saved to {dataset_path}.")