import pydantic
from datetime import datetime
from domain.category import Category


class ArticleTopic(pydantic.BaseModel):
  id: str
  topic: str


# most fields can be None, because
# they can be excluded from the search and are not always returned
class Article(pydantic.BaseModel):
  id: str
  url: str | None = None
  source: str | None = None
  publish_date: datetime | None = None
  image: str | None = None
  author: list[str] | None = None
  title: list[str] | None = None
  paragraphs: list[str] | None = None

  # analyzer part
  analyze_time: datetime | None = None

  # contains both the analyzed and the metadata categories
  categories: list[Category] | None = None

  # subset of 'categories', only contains the categories that were assigned by the analyzer
  analyzed_categories: list[Category] | None = None 
  embeddings: list[float] | None = None
  entities: list[str] | None = None

  # topics part
  # topics are optional, will be added later by the topic modeler
  topics: list[ArticleTopic] | None = None


class ArticleList(pydantic.BaseModel):
  articles: list[Article]
  total_count: int
