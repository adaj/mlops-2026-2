FROM python:3.11-slim

WORKDIR /app

RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /app

RUN apt-get update && apt-get install -y build-essential libffi-dev && rm -rf /var/lib/apt/lists/*

USER appuser

ENV PATH="/home/appuser/.local/bin:$PATH"

# Cache do TF Hub fora do container (volume no docker-compose): o Universal
# Sentence Encoder (~300 MB) e baixado uma vez so, nao a cada rebuild
ENV TFHUB_CACHE_DIR=/home/appuser/tfhub_cache
RUN mkdir -p /home/appuser/tfhub_cache

RUN pip install --no-cache-dir --upgrade pip

COPY --chown=appuser:appuser requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser src ./src

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level","info"]