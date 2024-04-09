import os
import typing as t
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from embeddings import EmbeddingsModelContainer, EmbeddingsModel
from repository.elasticsearch_repository import ElasticsearchRepository
from dto.article_query import *
from dto.article_result import *
from dto.topic_query import *
from dto.topic_result import *
from dto.feed_query import *
from dto.category_result import *
from dto.category_query import *
from domain.article import *
from domain.topic import *
from repository import Repository

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

repo: Repository = ElasticsearchRepository(
  ELASTIC_CONN, 
  ELASTIC_USER, 
  ELASTIC_PASSWORD, 
  ELASTIC_CA_PATH, 
  not ELASTIC_TLS_INSECURE
)


log = log_utils.create_console_logger("Searcher")

app = FastAPI()

def map_to_article_results(article_list: ArticleList) -> ArticleResults:
  return ArticleResults(
    total=article_list.total_count,
    results=[ArticleResult(
      id=art.id,
      categories=art.categories,
      entities=art.entities,
      topics=[t.model_dump() for t in art.topics] if art.topics is not None else None, 
      url=art.url,
      publish_date=art.publish_date,
      source=art.source,
      image=art.image,
      author=art.author,
      title=art.title,
      paragraphs=art.paragraphs,
    ) for art in article_list.articles],
  )

def map_to_topic_results(topic_list: TopicList) -> TopicResults:
  return TopicResults(
    total=topic_list.total_count,
    results=[TopicResult(
      id=t.id,
      query=t.query.model_dump() if t.query is not None else None,
      topic=t.topic,
      count=t.count,
      representative_articles=[
          ta.model_dump() for ta in t.representative_articles
      ] if t.representative_articles is not None else None,
    ) for t in topic_list.topics]
   )

@app.post("/search/articles", response_model=ArticleResults, response_model_exclude_none=True)
async def search_articles(search_options: ArticleQuery) -> ArticleResults:

    log.info(f"searching for articles: {search_options}")

    search = search_options.search_type

    if search == ArticleQueryType.text:
      article_list = await repo.search_articles_text(search_options)
    elif search == ArticleQueryType.semantic:
      embeddings = em.encode([search_options.query])[0]
      article_list = await repo.search_articles_embeddings(search_options, embeddings)
    elif search == ArticleQueryType.combined:
      embeddings = em.encode([search_options.query])[0]
      article_list = await repo.search_articles_combined(search_options, embeddings)
    
    results = map_to_article_results(article_list) 
    return results

    
@app.post("/search/topics", response_model=TopicResults, response_model_exclude_none=True)
async def search_topics(topic_query: TopicQuery) -> TopicResults:

    log.info(f"searching for topics: {topic_query}")

    topic_list = await repo.search_topics(topic_query)

    results = map_to_topic_results(topic_list)
    return results


# @app.get("/feed", response_model=ArticleResults, response_model_exclude_none=True)
# async def get_feed(
#   page: int = 0,
#   page_size: int = 30, 
#   return_attributes: t.Annotated[list[str] | None, Query()] = None,
# ) -> ArticleResults:

#   print(return_attributes)

#   article_query = ArticleQuery(
#     page=page,
#     page_size=page_size,
#     return_attributes=return_attributes,
#   )

#   article_list = await repo.search_articles_text(article_query)
#   results = map_to_article_results(article_list)
#   return results
  

@app.get("/categories", response_model=CategoryResults, response_model_exclude_none=True)
async def get_categories(size: int = 10) -> CategoryResults:

  category_query = CategoryQuery(size=size)
  category_results = await repo.get_categories(category_query)  
  return category_results
