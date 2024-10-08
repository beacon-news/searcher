from pydantic import BaseModel
from datetime import datetime


class ArticleResult(BaseModel):
  # what's returned is based on the return_attributes field of the ArticleQuery
  id: str | None = None
  categories: list[dict] | None = None
  topics: list[dict] | None = None
  url: str | None = None
  publish_date: datetime | None = None
  source: str | None = None
  image: str | None = None
  author: str | None = None
  title: str | None = None
  paragraphs: list[str] | None = None


class ArticleResults(BaseModel):
  total: int
  results: list[ArticleResult]
