import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from embeddings import EmbeddingsModelContainer, EmbeddingsModel
from repository.elasticsearch_repo import ElasticsearchRepository

from utils import log_utils

load_dotenv()

def check_env(name: str, default=None) -> str:
  value = os.environ.get(name, default)
  if value is None:
    raise ValueError(f'{name} environment variable is not set')
  return value


EMBEDDINGS_MODEL_PATH = check_env('EMBEDDINGS_MODEL_PATH')

ELASTIC_USER = check_env('ELASTIC_USER', 'elastic')
ELASTIC_PASSWORD = check_env('ELASTIC_PASSWORD')
ELASTIC_CONN = check_env('ELASTIC_HOST', 'https://localhost:9200')
ELASTIC_CA_PATH = check_env('ELASTIC_CA_PATH', '../certs/_data/ca/ca.crt')
ELASTIC_TLS_INSECURE = bool(check_env('ELASTIC_TLS_INSECURE', False))

ec = EmbeddingsModelContainer.load(EMBEDDINGS_MODEL_PATH)
em = EmbeddingsModel(ec)


es = ElasticsearchRepository(
  ELASTIC_CONN, 
  ELASTIC_USER, 
  ELASTIC_PASSWORD, 
  ELASTIC_CA_PATH, 
  not ELASTIC_TLS_INSECURE
)


log = log_utils.create_console_logger("Searcher")


app = FastAPI()

class SearchOptions(BaseModel):
    query: str

@app.post("/search")
async def search(search_options: SearchOptions):
    # Assuming some search logic here based on the received search_options
    query = search_options.query
    
    # Placeholder response, replace with actual search logic
    # For demonstration, just returning the received search options

    embeddings = em.encode([query])[0]

    resp = es.es.search(
      index="articles", 
      knn={
        "field": "analyzer.embeddings",
        "query_vector": embeddings,
        "num_candidates": 50,
        "k": 10,
      },
      source_excludes=["analyzer.embeddings"],
    )

    print(resp)

    return resp  
    
    return {"query": "done"}
