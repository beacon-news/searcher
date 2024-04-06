import pydantic
from datetime import datetime
from domain.topic import *

# subset of topic, appended to the articles
class ArticleTopic(pydantic.BaseModel):
  id: str
  topic: str

# every field other than the 'id' can be None, because
# they can be excluded from the search
class Article(pydantic.BaseModel):
  id: str
  url: str | None = None
  publish_date: datetime | None = None
  author: str | None = None
  title: str | None = None
  paragraphs: list[str] | None = None

  categories: list[str] | None = None
  entities: list[str] | None = None
  embeddings: list[float] | None = None
  
  topics: list[ArticleTopic] | None = None
