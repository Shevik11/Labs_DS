FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HF_HOME=/tmp/huggingface TRANSFORMERS_CACHE=/tmp/huggingface/hub \
    HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false MODELS_DIR=/models
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.6.0 \
    && pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
COPY --chown=10001:10001 . /app
USER 10001:10001
EXPOSE 8144
HEALTHCHECK --interval=15s --timeout=5s --start-period=120s --retries=12 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8144/health',timeout=4)"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8144", "--workers", "1", "--no-access-log"]
