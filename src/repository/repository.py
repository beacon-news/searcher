from abc import ABC, abstractmethod
from dto.article_query import ArticleQuery
from dto.topic_query import TopicQuery
from domain.article import ArticleList
from domain.topic import TopicList
from dto.category_result import CategoryResults
from dto.category_query import CategoryQuery


class Repository(ABC):

  @abstractmethod
  async def search_articles_combined(self, article_query: ArticleQuery, embeddings: list) -> ArticleList:
    """Lexical and semantic search combined."""
    raise NotImplementedError

  @abstractmethod
  async def search_articles_text(self, article_query: ArticleQuery) -> ArticleList:
    """Lexical search."""
    raise NotImplementedError
  
  @abstractmethod
  async def search_articles_embeddings(self, article_query: ArticleQuery, embeddings: list) -> ArticleList:
    """Only semantic search, with only filters applied from the article query."""
    raise NotImplementedError
  
  @abstractmethod
  async def search_topics(self, topic_query: TopicQuery) -> TopicList:
    raise NotImplementedError
  
  # TODO: this returns a DTO, not a domain model 
  @abstractmethod
  async def get_categories(self, category_query: CategoryQuery) -> CategoryResults:
    raise NotImplementedError