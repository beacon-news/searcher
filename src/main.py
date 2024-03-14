import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, model_validator, ValidationError
from datetime import datetime
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
  # for title and paragraph
  query: str | None = None

  categories: str | None = None

  author: str | None = None

  # TODO: add tags to scrape_configs and elastic
  tags: str | None = None

  # ISO8601 date format, see pydantic docs
  date_min: datetime = datetime.fromtimestamp(0)
  date_max: datetime = datetime.now()

  @model_validator(mode='after')
  def some_query_must_be_present(self):
    
    values = [
      self.query,
      self.categories,
      self.author,
      self.tags
    ]
    for v in values:
      if v is not None and v.strip() != "":
        return self
    
    raise ValueError(f"at least one of 'query', 'categories', 'author' or 'tags' must not be empty")
  

def build_text_query(search_options: SearchOptions) -> dict:
    query = search_options.query
    categories = search_options.categories
    author = search_options.author
    date_min = search_options.date_min
    date_max = search_options.date_max

    should_queries = []
    if query:
      should_queries.append(
        {
          "match": {
            "article.paragraphs": query,
          }
        },
        {
          "match": {
            "article.title": query,
            "boost": 2,
          }
        },
      )
    
    if categories:
      should_queries.append(
        {
          "match": {
            "article.categories": categories,
          }
        }
      )
    
    if author:
      should_queries.append(
        {
          "match": {
            "article.author": author
          }
        }
      )
    
    date_query = {
      "range": {
        "article.publish_date": {
          "gte": date_min.isoformat(),
          "lte": date_max.isoformat(),
        }
      }
    }

    return {
      "bool": {
        "should": should_queries,
        "must": date_query,
      }
    }



def build_knn_query(search_options: SearchOptions) -> dict | None:

    if search_options.query is None or search_options.query.strip() == "": 
      return None

    embeddings = em.encode([])[0]
    return {
      "field": "analyzer.embeddings",
      "query_vector": embeddings,
      "num_candidates": 50,
      "k": 10,
    }



# def re_rank(res1, res2) -> dict: 


@app.post("/search")
async def search(search_options: SearchOptions):
    
    text_query = build_text_query(search_options)
    knn_query = build_knn_query(search_options)

    text_res = es.es.search(
      index="articles", 
      query=text_query,
      source_excludes=["analyzer.embeddings"],
    )

    em_res = es.es.search(
      index="articles", 
      knn=knn_query,
      source_excludes=["analyzer.embeddings"],
    )

    k = 0
    sorted_docs = {}
    for i, r in enumerate(text_res['hits']['hits']):
      # print(r)
      sorted_docs[r['_id']] = {
        'doc': r,
        'rank': 1.0 / (k + i+1)
      }
    
    e_res = {}
    for i, r in enumerate(em_res['hits']['hits']):
      id = r['_id']
      if id in sorted_docs:
        sorted_docs[id]['rank'] += 1.0 / (k + i+1)
      else:
        sorted_docs[id] = {
          'doc': r,
          'rank': 
        }

     

    print(t_res)
    return {'t': 't'}


    resp = es.es.search(
      index="articles", 
      query=text_query,
      knn=knn_query,
      rank={
        # TODO: see this in a bit more detail
        "rrf": {}
      },
      source_excludes=["analyzer.embeddings"],
    )

    print(resp)

    return resp  
    
    return {"query": "done"}
