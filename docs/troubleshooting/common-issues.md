# troubleshooting guide

## 0. module import errors when launching streamlit

- **Symptom**: `ModuleNotFoundError: No module named 'dashboard'` when running Streamlit directly.
- **Verification**: Run `python run_dashboard.py` from the repository root.

## 1. model lock mismatch or missing cache

- **Symptom**: `ModelNotLocked` exception raised by `LockedEncoder`.
- **Verification**: Check `models.lock` for the 40-character SHA hash of `Qwen/Qwen3-Embedding-0.6B`.

## 2. pseudonym mapping path inside repository

- **Symptom**: `ValueError: The pseudonym mapping must be kept outside the repository`.
- **Verification**: Confirm `PSEUDONYM_MAP_PATH` points outside the repository root.

## 3. the pinned model cannot be loaded

- **Symptom**: `ModelUnavailable` naming the model, the revisions installed locally and the install command.
- **Fix**: Run `python setup.py`. If the machine is offline but the model is cached, set `HF_HUB_OFFLINE=1`.
- **Verification**: `python setup.py` ends with `Bootstrap passed`.

## 4. drift cut-offs not found

- **Symptom**: `FileNotFoundError: Drift cut-offs not found` from `app.drift.drift_calculator`.
- **Fix**: Run `python -m app.drift.threshold_calibration` first. There is no default threshold.
- **Verification**: `evaluation/results/drift_thresholds.json` exists and names the model in `models.lock`.

## 5. no pseudonymised forms

- **Symptom**: `FileNotFoundError: No .docx forms in ...pseudonymised...` from an analysis step, or tests skipped
  with "pseudonymised forms not generated".
- **Fix**: Run `python -m app.ingestion.pseudonymiser`, or the whole pipeline.
- **Verification**: `data/processed/pseudonymised/proposals` holds as many files as the raw proposals folder.
