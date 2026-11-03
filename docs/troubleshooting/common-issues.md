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
