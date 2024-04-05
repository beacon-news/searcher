import os
from dotenv import load_dotenv
from fastapi import FastAPI
from embeddings import EmbeddingsModelContainer, EmbeddingsModel
from repository.elasticsearch_repository import ElasticsearchRepository
from dto.article_query import *
from dto.article_result import *

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

em = EmbeddingsModel(EmbeddingsModelContainer.load(EMBEDDINGS_MODEL_PATH))

es = ElasticsearchRepository(
  ELASTIC_CONN, 
  ELASTIC_USER, 
  ELASTIC_PASSWORD, 
  ELASTIC_CA_PATH, 
  not ELASTIC_TLS_INSECURE
)


log = log_utils.create_console_logger("Searcher")

app = FastAPI()

@app.post("/search/articles")
async def search_articles(search_options: ArticleQuery) -> ArticleResults:

    log.info(f"searching for {search_options}")

    search = search_options.search_type

    if search == ArticleQueryType.text:
      return await es.search_text(search_options)
    elif search == ArticleQueryType.semantic:
      embeddings = em.encode([search_options.query])[0]
      return await es.search_embeddings(search_options, embeddings)
    elif search == ArticleQueryType.combined:
      embeddings = em.encode([search_options.query])[0]
      return await es.search_combined(search_options, embeddings)
    