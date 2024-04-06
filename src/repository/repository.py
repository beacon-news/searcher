from abc import ABC, abstractmethod
from dto.article_query import ArticleQuery
from dto.article_result import ArticleResults
from dto.topic_query import TopicQuery


class Repository(ABC):

  @abstractmethod
  async def search_articles_combined(self, article_query: ArticleQuery, embeddings: list) -> ArticleResults:
    """Textual and semantic search combined."""
    raise NotImplementedError

  @abstractmethod
  async def search_articles_text(self, article_query: ArticleQuery) -> ArticleResults:
    """Textual search."""
    raise NotImplementedError
  
  @abstractmethod
  async def search_articles_embeddings(self, article_query: ArticleQuery, embeddings: list) -> ArticleResults:
    """Only semantic search, with only filters applied from the article query."""
    raise NotImplementedError
  
  @abstractmethod
  async def search_topics(self, topic_query: TopicQuery) -> TopicResults:
    raise NotImplementedError