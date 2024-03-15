from pydantic import BaseModel
from datetime import datetime

class SearchResult(BaseModel):
  id: str
  categories: list[str]
  entities: list[str]
  url: str
  publish_date: datetime
  author: str
  title: str
  paragraphs: list[str]

class SearchResults(BaseModel):
  results: list[SearchResult]
