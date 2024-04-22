import pydantic
from datetime import datetime


# subset of article
class TopicArticle(pydantic.BaseModel):
  id: str
  url: str
  image: str | None
  publish_date: datetime
  author: list[str]
  title: list[str]


class PublishDateFilter(pydantic.BaseModel):
  start: datetime
  end: datetime


class TopicArticleQuery(pydantic.BaseModel):
  publish_date: PublishDateFilter


# every field other than the 'id' can be None, because
# they can be excluded from the search and are not always returned
class Topic(pydantic.BaseModel):
  id: str
  batch_id: str | None = None
  batch_query: TopicArticleQuery | None = None
  create_time: datetime | None = None
  topic: str | None = None
  count: int | None = None
  representative_articles: list[TopicArticle] | None = None


class TopicList(pydantic.BaseModel):
  total_count: int
  topics: list[Topic]