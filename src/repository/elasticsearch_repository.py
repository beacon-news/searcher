from utils import log_utils
import logging
import asyncio
from elasticsearch import exceptions, AsyncElasticsearch
from dto.article_query import ArticleQuery
from dto.topic_query import TopicQuery
from repository.repository import Repository
from domain.article import *
from domain.topic import *

KNN_NUM_CANDIDATES = 50
KNN_K = 10


class ElasticsearchRepository(Repository):

  @classmethod
  def configure_logging(cls, level: int):
    cls.loglevel = level
    cls.log = log_utils.create_console_logger(
      name=cls.__name__,
      level=level
    )
  
  # map the returned attributes based on these mappings
  article_search_keys_to_repo_model = {
    "id": "_id",
    "categories": "analyzer.categories",
    "entities": "analyzer.entities",
    "url": "article.url",
    "publish_date": "article.publish_date",
    "author": "article.author",
    "title": "article.title",
    "paragraphs": "article.paragraphs",
  }

  topic_search_keys_to_repo_model = {
    "id": "_id",
    "query": "query",
    "topic": "topic",
    "count": "count",
    "representative_articles": "representative_articles",
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
    self.article_index = "articles"
    self.topic_index = "topics"

    # TODO: secure with TLS
    # TODO: add some form of auth
    self.log.info(f"connecting to Elasticsearch at {conn}")
    self.es = AsyncElasticsearch(conn, basic_auth=(user, password), ca_certs=cacerts, verify_certs=verify_certs)
  

  # TODO: assert topic index
  async def assert_articles_index(self):
    try:
      self.log.info(f"creating/asserting index '{self.article_index}'")
      await self.es.indices.create(index=self.article_index, mappings={
        "properties": {
          "topics": {
            "properties": {
              "topic_ids": {
                "type": "keyword"
              },
              "topic_names": {
                "type": "text"
              }
            }
          },
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
        self.log.info(f"index {self.article_index} already exists")
  
  async def search_articles_combined(self, search_options: ArticleQuery, embeddings: list) -> list[Article]:
    res_text = asyncio.Task(self.__search_articles_text(search_options))
    res_em = asyncio.Task(self.__search_articles_embeddings(search_options, embeddings))
    res_text = await res_text
    res_em = await res_em

    if len(res_text) == 0:
      return self.__map_to_articles(res_em['hits']['hits'])
    elif len(res_em) == 0:
      return self.__map_to_articles(res_text['hits']['hits'])
    
    reranked = self.__re_rank_rrf(res_text['hits']['hits'], res_em['hits']['hits'])
    return self.__map_to_articles([doc['doc'] for doc in reranked])
  
  async def search_articles_text(self, search_options: ArticleQuery) -> list[Article]:
    res = await self.__search_articles_text(search_options)
    return self.__map_to_articles(res['hits']['hits'])
  
  async def __search_articles_text(self, search_options: ArticleQuery) -> list:
    text_query = self.__build_article_text_query(search_options)
    return await self.es.search(
      index=self.article_index, 
      query=text_query,
      size=search_options.size,
      source_excludes=["analyzer.embeddings"],
      source_includes=self.__map_search_keys(
        keys=search_options.return_attributes, 
        mapping=self.article_search_keys_to_repo_model
      )
    )
  
  async def search_articles_embeddings(self, search_options: ArticleQuery, embeddings: list) -> list[Article]:
    res = await self.__search_articles_embeddings(search_options, embeddings)
    return self.__map_to_articles(res['hits']['hits'])
  
  async def __search_articles_embeddings(self, search_options: ArticleQuery, embeddings: list) -> list:
    knn_query = self.__build_article_knn_query(search_options, embeddings)
    if knn_query is None:
      return []

    return await self.es.search(
      index=self.article_index, 
      knn=knn_query, 
      source_excludes=["analyzer.embeddings"],
      source_includes=self.__map_search_keys(
        keys=search_options.return_attributes, 
        mapping=self.article_search_keys_to_repo_model
      )
    )
  
  def __build_article_text_query(self, search_options: ArticleQuery) -> dict:
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
    
    date_query = self.__build_date_query(search_options.date_min, search_options.date_max)
    filters = [date_query]
    
    if id is not None:
      filters.append(self.__build_id_query(search_options.id)) 
    
    return {
      "bool": {
        "should": should_queries,
        "filter": filters,
      }
    }

  def __build_article_knn_query(self, search_options: ArticleQuery, embeddings: list) -> dict:
    filters = [self.__build_date_query(search_options)]
    if search_options.id is not None:
      filters.append(self.__build_id_query(search_options))

    return {
      "field": "analyzer.embeddings",
      "query_vector": embeddings,
      "num_candidates": KNN_NUM_CANDIDATES,
      "k": KNN_K,
      "filter": filters,
    }
    
  def __build_date_query(self, start: datetime, end: datetime) -> dict:
    return {
      "range": {
        "article.publish_date": {
          "gte": start.isoformat(),
          "lte": end.isoformat(),
        }
      }
    }
  
  def __build_id_query(self, id: str) -> dict:
    return {
      "term": {
        "_id": id
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

  def __map_search_keys(self, keys: list[str] | None, mapping: dict) -> list[str] | None:
    # reverse mapping from DTO keys to repo model
    if keys is None:
      # returns every key by default
      return None 
    return [mapping[key] for key in keys]

  def __map_to_articles(self, docs: list[dict]) -> list[Article]:
    # map from repo model to domain model

    res: list[Article] = []
    for doc in docs:
      source = doc['_source']
      id = doc.get('_id', None)

      if id is None:
        raise ValueError(f"no '_id' field found in doc: {doc}")

      article = Article(id=id)
      if 'article' in source:
        art = source['article']
        article.url = art.get('url', None)
        article.publish_date = art.get('publish_date', None)
        author = art.get('author', None)
        article.author = "\n".join(author) if author is not None else None
        title = art.get('title', None)
        article.title = "\n".join(title) if title is not None else None
        article.paragraphs = art.get('paragraphs', None)
      
      if 'analyzer' in source:
        # TODO: embeddings are never returned, they are excluded from every search
        analyzer = source['analyzer']
        article.categories = analyzer.get('categories', None)
        article.entities = analyzer.get('entities', None)
        article.embeddings = analyzer.get('embeddings', None)
      
      if 'topics' in source:
        topics = source['topics']

        article_topics = [ArticleTopic(
          id=id, 
          topic=topic) for id, topic in zip(topics['topic_ids'], topics['topic_names'])
        ]
        if len(article_topics) != 0:
          article.topics = article_topics

      res.append(article)

    return res

  async def search_topics(self, topic_query: TopicQuery) -> list[Topic]:
    query = self.__build_topic_query(topic_query)
    docs = await self.es.search(
      index=self.topic_index, 
      query=query,
      source_includes=self.__map_search_keys(
        keys=topic_query.return_attributes,
        mapping=self.topic_search_keys_to_repo_model
      )
    )
    return self.__map_to_topics(docs["hits"]["hits"])
  
  def __build_topic_query(self, topic_query: TopicQuery) -> dict:
    filters = []
    if topic_query.id is not None:
      filters.append(self.__build_id_query(topic_query.id))
    
    count_min = topic_query.count_min
    count_max = topic_query.count_max
    if count_min is not None or count_max is not None:
      count_query = {
        "range": {
          "count": {}
        }
      }
      if count_min is not None:
        count_query["range"]["count"]["gte"] = count_min
      if count_max is not None:
        count_query["range"]["count"]["lte"] = count_max
      filters.append(count_query)

    must_queries = []
    if topic_query.topic is not None:
      must_queries.append({
        "match": {
          "topic": topic_query.topic,
        }
      })

    return {
      "bool": {
        "must": must_queries,
        "filter": filters,
      }
    }
  
  def __map_to_topics(self, docs: list[dict]) -> list[Topic]:
    # convert to domain model

    res: list[Topic] = []
    for doc in docs:
      source = doc['_source']
      id = doc.get('_id', None)

      if id is None:
        raise ValueError(f"no '_id' field found in doc: {doc}")

      topic = Topic(id=id)
      topic.create_time = source.get('create_time', None)
      topic.topic = source.get('topic', None)

      if 'query' in source:
        topic.query = TopicArticleQuery(
          publish_date=PublishDateFilter(
            start=datetime.fromisoformat(source['query']['publish_date']['start']),
            end=datetime.fromisoformat(source['query']['publish_date']['end']),
          )
        )
      topic.count = source.get('count', None)

      if 'representative_articles' in source:
        topic.representative_articles = [
          TopicArticle(
            id=ra['_id'],
            url=ra['url'],
            publish_date=datetime.fromisoformat(ra['publish_date']),
            author=ra['author'],
            title=ra['title'],
          ) for ra in source['representative_articles']
        ]

      res.append(topic)

    return res
    hits = docs['hits']['hits']

    return [
      Topic(
        id=source['_id'],
        create_time=source['_source']['create_time'],
        query=TopicArticleQuery(
          publish_date=PublishDateFilter(
            start=datetime.fromisoformat(source['_source']['query']['publish_date']['start']),
            end=datetime.fromisoformat(source['_source']['query']['publish_date']['end']),
          )
        ),
        topic=source['_source']['topic'],
        count=source['_source']['count'],
        representative_articles=[
          TopicArticle(
            id=ra['_id'],
            url=ra['url'],
            publish_date=datetime.fromisoformat(ra['publish_date']),
            author=ra['author'],
            title=ra['title'],
          ) for ra in source['_source']['representative_articles']
        ]
      ) for source in hits
    ]