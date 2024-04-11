from dto.article_query import *
from dto.article_result import *
from dto.topic_query import *
from dto.topic_result import *
from dto.category_query import *
from dto.category_result import *
from domain.article import *
from domain.category import *
from domain.topic import *
from repository import Repository
from embeddings import EmbeddingsModel
from utils import log_utils
import logging


class SearchService:

  def __init__(self, repo: Repository, em: EmbeddingsModel, log_level: int = logging.INFO):
    self.log = log_utils.create_console_logger(
      name=self.__class__.__name__,
      level=log_level
    )
    self.repo = repo
    self.em = em

  async def search_articles(self, article_query: ArticleQuery) -> ArticleResults:
    self.log.info(f"searching for articles: {article_query}")

    search = article_query.search_type

    if search == ArticleQueryType.text:
      article_list = await self.repo.search_articles_text(article_query)
    elif search == ArticleQueryType.semantic:
      embeddings = self.em.encode([article_query.query])[0]
      article_list = await self.repo.search_articles_embeddings(article_query, embeddings)
    elif search == ArticleQueryType.combined:
      embeddings = self.em.encode([article_query.query])[0]
      article_list = await self.repo.search_articles_combined(article_query, embeddings)
    
    results = self.__map_to_article_results(article_list) 
    return results
    
  def __map_to_article_results(self, article_list: ArticleList) -> ArticleResults:
    return ArticleResults(
      total=article_list.total_count,
      results=[ArticleResult(
        id=art.id,
        categories=[art.model_dump() for art in art.categories] if art.categories is not None else None, 
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

  async def search_topics(self, topic_query: TopicQuery) -> TopicResults:
    self.log.info(f"searching for topics: {topic_query}")

    topic_list = await self.repo.search_topics(topic_query)
    results =self.__map_to_topic_results(topic_list)
    return results
    
  def __map_to_topic_results(self, topic_list: TopicList) -> TopicResults:
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

  async def search_categories(self, category_query: CategoryQuery) -> CategoryResults:
    self.log.info(f"searching for categories: {category_query}")

    category_list = await self.repo.search_categories(category_query)  
    results = self.__map_to_category_results(category_list)
    return results

  def __map_to_category_results(self, category_list: CategoryList) -> CategoryResults:
    return CategoryResults(
      total=category_list.total_count,
      results=[CategoryResult(
        id=cat.id,
        name=cat.name,
      ) for cat in category_list.categories]
    )