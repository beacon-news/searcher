FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt --no-cache-dir

RUN useradd app --create-home --shell /bin/bash
USER app

COPY --chown=app:app . .

ENV EMBEDDINGS_MODEL_PATH=../models/embeddings/embeddings_container_all_MiniLM_L6_v2.pkl
ENV ELASTIC_PASSWORD=password

WORKDIR /app/src

ENTRYPOINT ["uvicorn", "searcher_main:app", "--host", "0.0.0.0", "--port", "8000"]
