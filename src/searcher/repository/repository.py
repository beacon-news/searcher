from abc import ABC, abstractmethod
from ..dto.article_query import ArticleQuery
from ..dto.topic_query import TopicQuery
from ..dto.topic_batch_query import TopicBatchQuery
from ..domain.article import ArticleList
from ..domain.topic import TopicList, TopicBatchList
from ..domain.category import CategoryList
from ..dto.category_query import CategoryQuery


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
  async def search_topic_batches(self, topic_batch_query: TopicBatchQuery) -> TopicBatchList:
    """Get topic batches."""
    raise NotImplementedError

  @abstractmethod
  async def search_topics(self, topic_query: TopicQuery) -> TopicList:
    """Search and filter for topics."""
    raise NotImplementedError
  
  @abstractmethod
  async def search_categories(self, category_query: CategoryQuery) -> CategoryList:
    """Get the categories that match the query."""
    raise NotImplementedError