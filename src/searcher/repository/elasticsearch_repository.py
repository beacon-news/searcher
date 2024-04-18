from ..utils import log_utils
import logging
import asyncio
from elasticsearch import exceptions, AsyncElasticsearch
from ..dto.article_query import ArticleQuery
from ..dto.topic_query import TopicQuery
from ..dto.category_query import *
from .repository import Repository
from ..domain.article import *
from ..domain.topic import *
from ..domain.category import *

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
    "id": "id_is_always_returned", # causes nothing to be returned for the 'id', but the source's '_id' is used which is always returned
    "categories": [
      "article.categories",
      "analyzer.category_ids",
    ],
    "entities": "analyzer.entities",
    "topics": "topics",
    "url": "article.url",
    "publish_date": "article.publish_date",
    "source": "article.source",
    "image": "article.image",
    "author": "article.author",
    "title": "article.title",
    "paragraphs": "article.paragraphs",
  }

  topic_search_keys_to_repo_model = {
    "id": "id_is_always_returned", # causes nothing to be returned for the 'id', but the source's '_id' is used which is always returned
    "query": "query",
    "topic": "topic",
    "count": "count",
    "representative_articles": "representative_articles",
  }

  topic_sort_options = {
    "track_scores": True,
    "sort": [
      {
        "count": {
          "order": "desc"
        }
      },
      {
        "_score": {
          "order": "desc"
        }
      },
      {
        "query.publish_date.end": {
          "order": "desc"
        }
      }
    ]
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
    self.articles_index = "articles"
    self.topics_index = "topics"
    self.categories_index = "categories"

    # TODO: secure with TLS
    # TODO: add some form of auth
    self.log.info(f"connecting to Elasticsearch at {conn}")
    self.es = AsyncElasticsearch(conn, basic_auth=(user, password), ca_certs=cacerts, verify_certs=verify_certs)
  

  # TODO: assert topic index
  async def assert_articles_index(self):
    try:
      self.log.info(f"creating/asserting index '{self.articles_index}'")
      await self.es.indices.create(index=self.articles_index, mappings={
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
              "category_ids": {
                # don't index the analyzer-generated categories, index the merged ones instead
                # only to be able to differentiate between the predicted and predefined categories
                "enabled": "false",
                "type": "keyword",
              },
              "embeddings": {
                "type": "dense_vector",
                "dims": 384, # depends on the embeddings model
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
              "source": {
                "type": "text",
                # keyword mapping needed so we can do aggregations
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "publish_date": {
                "type": "date",
              },
              "image": {
                "type": "keyword",
                "enabled": "false", # don't index image urls
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
              "categories": {
                "properties": {
                  "ids" : {
                    "type": "keyword"
                  },
                  "names": {
                    "type": "text",
                    # keyword mapping needed so we can do aggregations
                    "fields": {
                      "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                      }
                    }
                  }
                }
              },
              # "categories": {
              #   "type": "text",
              #   # keyword mapping needed so we can do aggregations
              #   "fields": {
              #     "keyword": {
              #       "type": "keyword",
              #       "ignore_above": 256
              #     }
              #   }
              # },
            }
          }
        }
      })
    except exceptions.BadRequestError as e:
      if e.message == "resource_already_exists_exception":
        self.log.info(f"index {self.articles_index} already exists")

  async def assert_categories_index(self):
    try:
      self.log.info(f"creating/asserting index '{self.categories_index}'")
      await self.es.indices.create(index=self.categories_index, mappings={
        "properties": {
          "name": {
            "type": "text",
          }
        }
      })
    except exceptions.BadRequestError as e:
      if e.message == "resource_already_exists_exception":
        self.log.info(f"index {self.categories_index} already exists")

  # TODO: add topic index assertion
  
  # TODO: in case of combined search, pagination doesn't really work as expected.
  # Pagination only applies to the text query,
  # the KNN query always returns the first 'K' most relevant results.
  # This leads to the KNN results being duplicated in the results, if we're looking
  # at the results across pages.
  # e.g. page 0, page size 12, KNN 10: 10 KNN results, 12 text results combined into first 12 results
  # page 1, page size 12, KNN 10: 10 KNN results, 12 NEXT text results combined into first 12 results
  # --> this can end in duplicating the KNN results

  # solution: disable pages, only consider the page size ?

  async def search_articles_combined(self, search_options: ArticleQuery, embeddings: list) -> ArticleList:
    res_text = asyncio.Task(self.__search_articles_text(search_options))
    res_em = asyncio.Task(self.__search_articles_embeddings(search_options, embeddings))
    res_text = await res_text
    res_em = await res_em

    res_text_count = res_text['hits']['total']['value']
    res_em_count = res_em['hits']['total']['value']

    if res_text_count == 0:
      return self.__map_to_articles(res_em['hits'])
    elif res_em_count == 0:
      return self.__map_to_articles(res_text['hits'])

    reranked_docs = self.__re_rank_rrf(res_text['hits']['hits'], res_em['hits']['hits'])
    # combine results, swapping parts out so it looks like a single result
    combined = res_text

    # precise total count cannot be provided because of overlap between the 2 queries, so the max is returned
    combined['hits']['total']['value'] = max(res_text_count, res_em_count)
    combined['hits']['hits'] = reranked_docs[:search_options.page_size]
    
    return self.__map_to_articles(combined['hits'])
  
  async def search_articles_text(self, search_options: ArticleQuery) -> ArticleList:
    res = await self.__search_articles_text(search_options)
    return self.__map_to_articles(res['hits'])
  
  async def __search_articles_text(self, search_options: ArticleQuery) -> dict:
    text_query = self.__build_article_text_query(search_options)
    sort_options = self.__build_article_sort_options(search_options)
    return await self.es.search(
      index=self.articles_index, 
      query=text_query,
      from_=search_options.page * search_options.page_size,
      size=search_options.page_size,
      sort=sort_options["sort"],
      track_scores=sort_options["track_scores"],
      source_excludes=["analyzer.embeddings"],
      source_includes=self.__map_search_keys(
        keys=search_options.return_attributes, 
        mapping=self.article_search_keys_to_repo_model
      )
    )
  
  async def search_articles_embeddings(self, search_options: ArticleQuery, embeddings: list) -> ArticleList:
    res = await self.__search_articles_embeddings(search_options, embeddings)
    return self.__map_to_articles(res['hits'])
  
  async def __search_articles_embeddings(self, search_options: ArticleQuery, embeddings: list) -> dict:
    knn_query = self.__build_article_knn_query(search_options, embeddings)
    sort_options = self.__build_article_sort_options(search_options)
    return await self.es.search(
      index=self.articles_index, 
      knn=knn_query, 
      sort=sort_options["sort"],
      track_scores=sort_options["track_scores"],
      source_excludes=["analyzer.embeddings"],
      source_includes=self.__map_search_keys(
        keys=search_options.return_attributes, 
        mapping=self.article_search_keys_to_repo_model
      )
    )
  
  def __build_article_text_query(self, search_options: ArticleQuery) -> dict:

    # query should match at least either the paragraphs or the title
    should_queries = []
    if search_options.query:
      should_queries.extend([
        {
          "match": {
            "article.paragraphs": search_options.query,
          }
        },
        {
          "match": {
            "article.title": {
              "query": search_options.query,
              "boost": 2,
            }
          }
        },
      ])
    
    # TODO: add this as filters as well?
    # categories, author, topic must match if provided, contribute to the score
    must_queries = []
    if search_options.source:
      must_queries.append(self.__build_article_source_query(search_options.source))
    
    if search_options.author:
      must_queries.append(self.__build_article_author_query(search_options.author))
    
    if search_options.categories:
      must_queries.append(self.__build_article_category_query(search_options.categories))

    if search_options.topic:
      must_queries.append(self.__build_article_topic_query(search_options.topic))
    
    # date, id, topic_id must match if provided, don't contribute to the score
    date_query = self.__build_date_query(
      field="article.publish_date",
      start=search_options.date_min, 
      end=search_options.date_max
    )
    filters = [date_query]
    
    if search_options.ids and len(search_options.ids) > 0:
      filters.append(self.__build_ids_query(search_options.ids)) 
    
    if search_options.category_ids:
      must_queries.append(self.__build_article_category_ids_query(search_options.category_ids))

    if search_options.topic_ids:
      filters.append(self.__build_article_topic_ids_query(search_options.topic_ids)) 
    
    return {
      "bool": {
        "must": must_queries,
        "should": should_queries,
        "minimum_should_match": 1 if len(should_queries) > 0 else 0, # either the paragraphs or the title must contain the searched query
        "filter": filters,
      }
    }

  def __build_article_knn_query(self, search_options: ArticleQuery, embeddings: list) -> dict:
    # every search option provided doesn't contribute to the score, 
    # the score is only calculated based on embedding cosine similarity

    filters = [self.__build_date_query(
      field="article.publish_date",
      start=search_options.date_min,
      end=search_options.date_max
    )]
    if search_options.ids and len(search_options.ids) > 0:
      filters.append(self.__build_ids_query(search_options.ids))
    
    if search_options.source:
      filters.append(self.__build_article_source_query(search_options.source))

    if search_options.author:
      filters.append(self.__build_article_author_query(search_options.author))

    if search_options.categories:
      filters.append(self.__build_article_category_query(search_options.categories))

    if search_options.category_ids:
      filters.append(self.__build_article_category_ids_query(search_options.category_ids))
    
    if search_options.topic:
      filters.append(self.__build_article_topic_query(search_options.topic))

    if search_options.topic_ids:
      filters.append(self.__build_article_topic_ids_query(search_options.topic_ids))
    

    return {
      "field": "analyzer.embeddings",
      "query_vector": embeddings,
      "num_candidates": KNN_NUM_CANDIDATES,
      "k": KNN_K,
      "filter": filters,
    }

  def __build_article_source_query(self, source: str) -> dict:
    return {
      "match": {
        "article.source": source
      }
    }

  def __build_article_category_ids_query(self, ids: list[str]) -> dict:
    return {
      "match": {
        "article.categories.ids": ids
      }
    }
  
  def __build_article_category_query(self, categories: str) -> dict:
    return {
      "match": {
        "article.categories.names": categories
      }
    }
  
  def __build_article_author_query(self, author: str) -> dict:
    return {
      "match": {
        "article.author": author
      }
    }
  
  def __build_article_topic_ids_query(self, ids: list[str]) -> dict:
    return {
      "terms": {
        "topics.topic_ids": ids
      }
    }
  
  def __build_article_topic_query(self, topic: str) -> dict:
    return {
      "match": {
        "topics.topic_names": topic
      }
    }
    
  def __build_date_query(self, field: str, start: datetime, end: datetime) -> dict:
    return {
      "range": {
        field: {
          "gte": start.isoformat(),
          "lte": end.isoformat(),
        }
      }
    }
  
  def __build_ids_query(self, ids: list[str]) -> dict:
    return {
      "terms": {
        "_id": ids
      }
    }
  
  def __build_article_sort_options(self, article_query: ArticleQuery) -> dict:
    # global sort options
    sort_options = {
      "track_scores": True,
      "sort": [
        {
          "_score": {
            "order": "desc"
          }
        }
      ],
    }

    # default sort 
    option = {
      "article.publish_date": {
        "order": "desc"
      }
    }
    if article_query.sort_field is not None and article_query.sort_dir is not None:
      option = {
        self.__map_search_keys([article_query.sort_field], self.article_search_keys_to_repo_model)[0]: {
          "order": article_query.sort_dir.value,
        }
      }
    sort_options["sort"].append(option)
    return sort_options

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
      
      return [v['doc'] for _, v in sorted(docs.items(), key=lambda doc: doc[1]['rank'], reverse=True)]

  def __map_search_keys(self, keys: list[str] | None, mapping: dict) -> list[str] | None:
    # reverse mapping from DTO keys to repo model
    if keys is None:
      # returns every key by default
      return None 

    mapped = []
    for k in keys:
      if type(mapping[k]) == str:
        mapped.append(mapping[k])
      elif type(mapping[k]) == list:
        mapped.extend(mapping[k])
    return mapped

  def __map_to_articles(self, doc_hits: dict) -> ArticleList:
    # map from repo model to domain model

    articles: list[Article] = []

    total_count = doc_hits['total']['value']

    for doc in doc_hits["hits"]:
      source = doc['_source']

      # at least the '_id' field should always be present
      id = doc.get('_id', None)

      if id is None:
        raise ValueError(f"no '_id' field found in doc: {doc}")

      article = Article(id=id)
      if 'article' in source:
        art = source['article']
        article.url = art.get('url', None)
        article.source = art.get('source', None)
        article.publish_date = art.get('publish_date', None)
        article.image = art.get('image', None)
        author = art.get('author', None)
        article.author = "\n".join(author) if author is not None else None
        title = art.get('title', None)
        article.title = "\n".join(title) if title is not None else None
        article.paragraphs = art.get('paragraphs', None)

        categories = art.get('categories', None)
        if categories:
          article.categories = [
            Category(
              id=id,
              name=name
            ) for id, name in zip(categories['ids'], categories['names'])
          ] 

      if 'analyzer' in source:
        # TODO: embeddings are never returned, they are excluded from every search
        analyzer = source['analyzer']
        article.entities = analyzer.get('entities', None)
        article.embeddings = analyzer.get('embeddings', None)

        # analyzed categories can only be constructed if the merged categories are present
        analyzer_category_ids = analyzer.get('category_ids', None)
        if analyzer_category_ids and article.categories:
          article.analyzed_categories = [cat for cat in article.categories if cat.id in analyzer_category_ids]
      
      if 'topics' in source:
        topics = source['topics']
        article_topics = [ArticleTopic(
          id=id, 
          topic=topic) for id, topic in zip(topics['topic_ids'], topics['topic_names'])
        ]
        if len(article_topics) != 0:
          article.topics = article_topics

      articles.append(article)

    res = ArticleList(articles=articles, total_count=total_count)
    return res 

  async def search_topics(self, topic_query: TopicQuery) -> TopicList:
    query = self.__build_topic_query(topic_query)
    docs = await self.es.search(
      index=self.topics_index, 
      query=query,
      sort=self.topic_sort_options["sort"],
      track_scores=self.topic_sort_options["track_scores"],
      from_=topic_query.page * topic_query.page_size,
      size=topic_query.page_size,
      source_includes=self.__map_search_keys(
        keys=topic_query.return_attributes,
        mapping=self.topic_search_keys_to_repo_model
      )
    )
    return self.__map_to_topics(docs["hits"])
  
  def __build_topic_query(self, topic_query: TopicQuery) -> dict:
    filters = []
    if topic_query.ids and len(topic_query.ids) > 0:
      filters.append(self.__build_ids_query(topic_query.ids))
    
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

    # query so that both the start and end is in the queried range
    filters.append(self.__build_date_query(
      field="query.publish_date.start",
      start=topic_query.date_min, 
      end=topic_query.date_max,
    ))
    filters.append(self.__build_date_query(
      field="query.publish_date.end",
      start=topic_query.date_min, 
      end=topic_query.date_max,
    ))

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

  # TODO:
  # def __build_topic_sort_options(self, topic_query: TopicQuery) -> dict:
  #   # global sort options
  #   sort_options = {
  #     "track_scores": True,
  #     "sort": [
  #       {
  #         "_score": {
  #           "order": "desc"
  #         }
  #       }
  #     ],
  #   }

  #   # default sort 
  #   option = {
  #     "query.publish_date.end": {
  #       "order": "desc"
  #     }
  #   }
  #   if topic_query.sort_field is not None and topic_query.sort_dir is not None:
  #     option = {
  #       self.__map_search_keys([topic_query.sort_field], self.topic_search_keys_to_repo_model)[0]: {
  #         "order": topic_query.sort_dir.value,
  #       }
  #     }
  #   sort_options["sort"].append(option)
  #   return sort_options
  
  def __map_to_topics(self, doc_hits: list[dict]) -> TopicList:
    # convert to domain model

    topics: list[Topic] = []
    total_count = doc_hits['total']['value']

    for doc in doc_hits['hits']:
      source = doc['_source']

      # at least the '_id' field should always be present
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

      topics.append(topic)

    res = TopicList(topics=topics, total_count=total_count)
    return res


  async def search_categories(self, category_query: CategoryQuery) -> CategoryList:
    query = self.__build_categories_query(category_query)
    docs = await self.es.search(
      index=self.categories_index,
      query=query,
      from_=category_query.page * category_query.page_size,
      size=category_query.page_size,
    )
    return self.__map_to_categories(docs['hits'])

  def __build_categories_query(self, category_query: CategoryQuery) -> dict:
    filter_queries = []
    if category_query.ids is not None and len(category_query.ids) > 0: 
      filter_queries.append(self.__build_ids_query(category_query.ids))
    
    should_queries = []
    if category_query.query is not None:
      should_queries.append(self.__build_category_name_query(category_query.query))

    return {
      "bool": {
        "should": should_queries,
        "minimum_should_match": 1 if len(should_queries) > 0 else 0,
        "filter": filter_queries,
      }
    }

  def __map_to_categories(self, doc_hits: list[dict]) -> CategoryList:
    categories: list[Category] = []
    total_count = doc_hits['total']['value']

    for doc in doc_hits['hits']:
      source = doc['_source']

      # the '_id' field should always be present
      id = doc.get('_id', None)
      if id is None:
        raise ValueError(f"no '_id' field found in doc: {doc}")

      # the 'name' field should always be present
      name = source.get('name', None)
      if name is None:
        raise ValueError(f"no 'name' field found in source of doc: {doc}")

      categories.append(Category(
        id=id, 
        name=name
      ))

    res = CategoryList(
      total_count=total_count,
      categories=categories
    )
    return res
    

  
  # async def __search_aggregate_categories(self, top_n: int) -> CategoryResults:
  #   result = await self.es.search(
  #     index=self.articles_index,
  #     aggs=self.__build_categories_aggregation(top_n),
  #     size=0, # don't return any articles, only the categories
  #   )

  #   buckets = result['aggregations']['categories']['buckets']

  #   res = CategoryResults(
  #     total=top_n,
  #     results=[CategoryResult(
  #       name=b['key'],
  #       article_count=b['doc_count'],
  #     ) for b in buckets],
  #   ) 
  #   return res

  # def __build_categories_aggregation(self, size: int) -> dict:
  #   # only get up to the top 'size' categories
  #   return {
  #     "categories": {
  #       "terms": {
  #         "field": "article.categories.names.keyword",
  #         "size": size,
  #       }
  #     }
  #   }
  
  def __build_category_name_query(self, name: str) -> dict:
    return {
      "match": {
        "name": name
      }
    }
  
  
  # async def __search_categories(self) -> CategoryResults:
  #   result = await self.es.search(
  #     index=self.categories_index,
  #     query={
  #       "match_all": {}
  #     },
  #   )

  #   res = CategoryResults(
  #     total=result['hits']['total']['value'],
  #     results=[CategoryResult(
  #       id=doc['_id'],
  #       name=doc['_source']['name'],
  #     ) for doc in result['hits']['hits']],
  #   )
  #   return res
    
  
  # def __build_match_all_query(self) -> dict:
  #   return {
  #     "match_all": {}
  #   }