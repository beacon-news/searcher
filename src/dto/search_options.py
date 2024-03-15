from pydantic import BaseModel, model_validator, conint
from datetime import datetime
from enum import Enum

class SearchType(str, Enum):
  text = "text"
  semantic = "semantic"
  combined = "combined"


class SearchOptions(BaseModel):
  # for title and paragraph
  query: str | None = None

  categories: str | None = None

  author: str | None = None

  # TODO: add tags to scrape_configs and elastic
  tags: str | None = None

  # ISO8601 date format, see pydantic docs
  date_min: datetime = datetime.fromtimestamp(0)
  date_max: datetime = datetime.now()

  # only applicable to text search
  size: conint(gt=0, lt=30) = 10 # type: ignore

  search_type: SearchType = SearchType.text

  @model_validator(mode='after')
  def some_query_must_be_present(self):
    
    values = [
      self.query,
      self.categories,
      self.author,
      self.tags
    ]
    for v in values:
      if v is not None and v.strip() != "":
        return self
    
    raise ValueError(f"at least one of 'query', 'categories', 'author' or 'tags' must not be empty")
  
  @model_validator(mode='after')
  def query_present_for_semantic_and_combined_search(self):
    if (
      self.search_type == SearchType.semantic or self.search_type == SearchType.combined and (
        self.query is None or self.query.strip() == ""
      )
    ):
      raise ValueError(f"'query' must not be empty for 'semantic' or 'combined' search")
    return self

  
