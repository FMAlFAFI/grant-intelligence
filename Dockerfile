# Grant Intelligence dashboard (Streamlit).
# Build and start:  docker compose up --build        then open http://localhost:8501
# Fill it with data: docker compose --profile pipeline run --rm pipeline

# Same interpreter as .python-version
FROM python:3.11.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Run as an unprivileged user
RUN useradd --create-home --uid 1000 app

# Dependencies first, so this layer is rebuilt only when requirements.txt changes.
# No pip cache in the image. The extra index offers the CPU-only build of the pinned torch version,
# which is several times smaller than the default build with GPU libraries; the encoder runs on CPU.
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Application code. Data, results, logs and .env are kept out by .dockerignore.
COPY --chown=app:app . .

# Folders that are mounted as volumes at run time, owned by the application user, who also has to be
# able to write new files in /app. The pseudonym mapping and the model cache live under the home
# folder, outside the application folder.
RUN mkdir -p data/raw data/processed results logs \
        /home/app/.cache/huggingface /home/app/grant-intelligence-private \
    && chown app:app /app \
    && chown -R app:app /app/data /app/results /app/logs /home/app

USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3)"

# The dashboard only. It listens on every interface so the published port reaches it.
CMD ["python", "-m", "streamlit", "run", "dashboard/streamlit_app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
