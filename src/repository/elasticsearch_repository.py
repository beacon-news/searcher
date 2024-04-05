from utils import log_utils
import logging
import asyncio
from elasticsearch import exceptions, AsyncElasticsearch
from dto.article_query import ArticleQuery
from dto.article_result import ArticleResult, ArticleResults

KNN_NUM_CANDIDATES = 50
KNN_K = 10


class ElasticsearchRepository:

  @classmethod
  def configure_logging(cls, level: int):
    cls.loglevel = level
    cls.log = log_utils.create_console_logger(
      name=cls.__name__,
      level=level
    )
  
  # map the returned attributes based on this
  article_result_keys_to_repo_model = {
    "id": "_id",
    "categories": "analyzer.categories",
    "entities": "analyzer.entities",
    "url": "article.url",
    "publish_date": "article.publish_date",
    "author": "article.author",
    "title": "article.title",
    "paragraphs": "article.paragraphs",
  }

  def __init__(
      self, 
      conn: str, 
      user: str, 
      password: str, 
      cacerts: str, 
      verify_certs: bool = True,
      log_level: int = logging.INFO
  ):
    self.configure_logging(log_level)
    self.index_name = "articles"

    # TODO: secure with TLS
    # TODO: add some form of auth
    self.log.info(f"connecting to Elasticsearch at {conn}")
    self.es = AsyncElasticsearch(conn, basic_auth=(user, password), ca_certs=cacerts, verify_certs=verify_certs)

  async def assert_index(self):
    # assert articles index
    try:
      self.log.info(f"creating/asserting index '{self.index_name}'")
      await self.es.indices.create(index=self.index_name, mappings={
        "properties": {
          "analyzer": {
            "properties": {
              "categories": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "embeddings": {
                "type": "dense_vector",
                "dims": 384, # depends on model used
              },
              "entities": {
                "type": "text"
              },
            }
          },
          "article": {
            "properties": {
              "id": {
                "type": "keyword",
              },
              "url": {
                "type": "keyword",
              },
              "publish_date": {
                "type": "date",
              },
              "author": {
                "type": "text",
              },
              "title": {
                "type": "text",
              },
              "paragraphs": {
                "type": "text",
              },
            }
          }
        }
      })
    except exceptions.BadRequestError as e:
      if e.message == "resource_already_exists_exception":
        self.log.info(f"index {self.index_name} already exists")
  
  async def search_combined(self, search_options: ArticleQuery, embeddings: list) -> ArticleResults:
    res_text = asyncio.Task(self.__search_text(search_options))
    res_em = asyncio.Task(self.__search_embeddings(search_options, embeddings))
    res_text = await res_text
    res_em = await res_em

    if len(res_text) == 0:
      return self.__create_result(res_em['hits']['hits'])
    elif len(res_em) == 0:
      return self.__create_result(res_text['hits']['hits'])
    
    reranked = self.__re_rank_rrf(res_text['hits']['hits'], res_em['hits']['hits'])
    return self.__create_result([doc['doc'] for doc in reranked])
  
  async def search_text(self, search_options: ArticleQuery) -> ArticleResults:
    res = await self.__search_text(search_options)
    return self.__create_result(res['hits']['hits'])
  
  async def __search_text(self, search_options: ArticleQuery) -> list:
    text_query = self.__build_text_query(search_options)
    return await self.es.search(
      index="articles", 
      query=text_query,
      size=search_options.size,
      source_excludes=["analyzer.embeddings"],
      source_includes=self.__map_search_keys(search_options.return_attributes)
    )
  
  async def search_embeddings(self, search_options: ArticleQuery, embeddings: list) -> ArticleResults:
    res = await self.__search_embeddings(search_options, embeddings)
    return self.__create_result(res['hits']['hits'])
  
  async def __search_embeddings(self, search_options: ArticleQuery, embeddings: list) -> list:
    knn_query = self.__build_knn_query(search_options, embeddings)
    if knn_query is None:
      return []

    return await self.es.search(
      index="articles", 
      knn=knn_query, 
      source_excludes=["analyzer.embeddings"],
      source_includes=self.__map_search_keys(search_options.return_attributes)
    )
  
  def __build_text_query(self, search_options: ArticleQuery) -> dict:
    id = search_options.id
    query = search_options.query
    categories = search_options.categories
    author = search_options.author

    should_queries = []
    if query:
      should_queries.extend([
        {
          "match": {
            "article.paragraphs": query,
          }
        },
        {
          "match": {
            "article.title": {
              "query": query,
              "boost": 2,
            }
          }
        },
      ])
    
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
    
    date_query = self.__build_date_query(search_options)
    filter_queries = [date_query]
    
    if id is not None:
      filter_queries.append(self.__build_id_query(search_options)) 
    
    return {
      "bool": {
        "should": should_queries,
        "filter": filter_queries,
      }
    }

  def __build_knn_query(self, search_options: ArticleQuery, embeddings: list) -> dict:
    filter_queries = [self.__build_date_query(search_options)]
    if search_options.id is not None:
      filter_queries.append(self.__build_id_query(search_options))

    return {
      "field": "analyzer.embeddings",
      "query_vector": embeddings,
      "num_candidates": KNN_NUM_CANDIDATES,
      "k": KNN_K,
      "filter": filter_queries,
    }
    
  def __build_date_query(self, search_options: ArticleQuery) -> dict:
    return {
      "range": {
        "article.publish_date": {
          "gte": search_options.date_min.isoformat(),
          "lte": search_options.date_max.isoformat(),
        }
      }
    }
  
  def __build_id_query(self, search_options: ArticleQuery) -> dict:
    return {
      "term": {
        "_id": search_options.id
      }
    }

  def __re_rank_rrf(self, res1, res2) -> dict: 
      k = 60
      docs = {}
      for i, r in enumerate(res1):
        docs[r['_id']] = {
          'doc': r,
          'rank': 1.0 / (k + i+1)
        }
      
      for i, r in enumerate(res2):
        id = r['_id']
        if id in docs:
          docs[id]['rank'] += 1.0 / (k + i+1)
        else:
          docs[id] = {
            'doc': r,
            'rank': 1.0 / (k + i+1) 
          }
      
      return [v for _, v in sorted(docs.items(), key=lambda doc: doc[1]['rank'], reverse=True)]

  def __map_search_keys(self, article_result_keys: list[str] | None) -> list[str] | None:
    # reverse mapping from DTO keys to repo model
    if article_result_keys is None:
      # returns every key by default
      return None 
    return [self.article_result_keys_to_repo_model[key] for key in article_result_keys]

  def __create_result(self, docs: list[dict]) -> ArticleResults:
    # map from repo model to DTO
    res = []
    for doc in docs:
      source = doc['_source']

      id = doc.get('_id', None)
      categories = source.get('analyzer', {}).get('categories', None)
      entities = source.get('analyzer', {}).get('entities', None)

      url = source.get('article', {}).get('url', None)
      publish_date = source.get('article', {}).get('publish_date', None)

      author = source.get('article', {}).get('author', None)
      author = "\n".join(author) if author is not None else None

      title = source.get('article', {}).get('title', None)
      title = "\n".join(title) if title is not None else None

      paragraphs = source.get('article', {}).get('paragraphs', None)

      res.append(
        ArticleResult(
          id=id,
          categories=categories,
          entities=entities,
          url=url,
          publish_date=publish_date,
          author=author,
          title=title,
          paragraphs=paragraphs,
        )
      )

    return ArticleResults(results=res)

  # async def store_batch(self, analyzed_articles: list[dict]) -> list[str]:
  #   self.log.info(f"attempting to insert {len(analyzed_articles)} articles in {self.index_name}")
  #   async for ok, action in helpers.async_streaming_bulk(self.es, self.__generate_doc_actions(analyzed_articles)):
  #     if not ok:
  #       self.log.error(f"failed to bulk store article: {action}")
  #       continue
  #     self.log.info(f"successfully stored article: {action}")
  
  # def __generate_doc_actions(self, articles: list[dict]):
  #   for i in range(len(articles)):
  #     action = {
  #       "_id": articles[i]["article"]["id"],
  #       "_index": self.index_name,
  #       **articles[i]
  #     }
  #     yield action

