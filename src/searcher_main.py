import os
import typing as t
from dotenv import load_dotenv
from fastapi import FastAPI
from embeddings import EmbeddingsModelContainer, EmbeddingsModel
from repository.elasticsearch_repository import ElasticsearchRepository
from dto.article_query import *
from dto.article_result import *
from dto.topic_query import *
from dto.topic_result import *
from dto.category_result import *
from dto.category_query import *
from domain.article import *
from domain.topic import *
from domain.category import *
from service import SearchService
from repository import Repository


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

repo: Repository = ElasticsearchRepository(
  ELASTIC_CONN, 
  ELASTIC_USER, 
  ELASTIC_PASSWORD, 
  ELASTIC_CA_PATH, 
  not ELASTIC_TLS_INSECURE
)

search_service = SearchService(
  repo=repo,
  em=em
)

tags_metadata = [
   {
      "name": "Search",
      "description": "Search various objects."
   }
]

app = FastAPI(
  openapi_tags=tags_metadata,
  prefix="/api/v1/search"
)


@app.post(
  "/search/articles",
  tags=["Search"],
  response_model=ArticleResults,
  response_model_exclude_none=True,
)
async def search_articles(search_options: ArticleQuery | None = ArticleQuery()) -> ArticleResults:
  return await search_service.search_articles(search_options)


    
@app.post(
  "/search/topics", 
  tags=["Search"],
  response_model=TopicResults, 
  response_model_exclude_none=True
)
async def search_topics(topic_query: TopicQuery | None = TopicQuery()) -> TopicResults:
  return await search_service.search_topics(topic_query)


@app.post(
  "/search/categories", 
  tags=["Search"],
  response_model=CategoryResults, 
  response_model_exclude_none=True,
)
async def search_categories(category_query: CategoryQuery | None = CategoryQuery()) -> CategoryResults:
  return await search_service.search_categories(category_query)