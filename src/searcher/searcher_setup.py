import os
import asyncio
from threading import Thread
from dotenv import load_dotenv
from .embeddings import EmbeddingsModelContainer, EmbeddingsModel
from .repository.elasticsearch_repository import ElasticsearchRepository
from .service import SearchService
from .repository import Repository


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
ELASTIC_CA_PATH = check_env('ELASTIC_CA_PATH', 'certs/_data/ca/ca.crt')
ELASTIC_TLS_INSECURE = bool(check_env('ELASTIC_TLS_INSECURE', False))

CORS_ALLOWED_ORIGINS = check_env('CORS_ALLOWED_ORIGINS', 'http://localhost').split(' ')
CORS_ALLOWED_METHODS = check_env('CORS_ALLOWED_METHODS', '*').split(' ')
CORS_ALLOWED_HEADERS = check_env('CORS_ALLOWED_HEADERS', '*').split(' ')
CORS_ALLOW_CREDENTIALS = bool(check_env('CORS_ALLOW_CREDENTIALS', 'true') == 'true')

embeddings_model = EmbeddingsModel(EmbeddingsModelContainer.load(EMBEDDINGS_MODEL_PATH))

repository: Repository = ElasticsearchRepository(
  ELASTIC_CONN, 
  ELASTIC_USER, 
  ELASTIC_PASSWORD, 
  ELASTIC_CA_PATH, 
  not ELASTIC_TLS_INSECURE
)

# assert indices
t = Thread(target=lambda: asyncio.run(repository.assert_indices()))
t.start()
t.join()

search_service = SearchService(
  repo=repository,
  em=embeddings_model,
)