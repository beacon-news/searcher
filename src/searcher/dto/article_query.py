from pydantic import BaseModel, model_validator, field_validator, Field
from typing import Annotated
from datetime import datetime
from enum import Enum
from .article_result import ArticleResult
from .sort_direction import SortDirection
from .utils import flatten_model_attributes

  
# find out the flattened keys of ArticleResult
article_search_keys = set()
flatten_model_attributes(ArticleResult, article_search_keys)

# keys of ArticleResult that make sense to sort by
article_sort_keys = set([
  "publish_date",
])


# model classes
class ArticleQueryType(str, Enum):
  text = "text"
  semantic = "semantic"
  combined = "combined"


class ArticleQuery(BaseModel):
  ids: list[str] | None = None

  # for title and paragraph
  query: str | None = None

  category_ids: list[str] | None = None
  categories: str | None = None

  source: str | None = None

  author: str | None = None

  # ISO8601 date format, see pydantic docs
  date_min: datetime = datetime.fromisoformat('1000-01-01T00:00:00')
  date_max: datetime = datetime.now()

  topic_ids: list[str] | None = None
  topic: str | None = None

  # pagination
  page: Annotated[int, Field(ge=0)] = 0

  # only applicable to text search, semantic search will always limit the returned results
  page_size: Annotated[int, Field(ge=1, le=40)] = 10

  # sorting
  sort_field: str | None = None
  sort_dir: SortDirection | None = None

  search_type: ArticleQueryType = ArticleQueryType.text

  # return only a subset of an ArticleResult
  # None means return all attributes
  return_attributes: list[str] | None = None  


  @field_validator("return_attributes")
  @classmethod
  def validate_return_attributes(cls, v: list[str] | None) -> list[str] | None:
    if v is None or len(v) == 0:
      return None

    for key in v:
      if key not in article_search_keys:
        raise ValueError(f"Invalid return attribute '{key}'. Must be one of {article_search_keys}.")

    # all keys are valid, return them
    return v

  @field_validator("sort_field")
  @classmethod
  def is_sortable_key(cls, v: str | None) -> str | None:
    if v is None:
      return None

    if v not in article_sort_keys:
      raise ValueError(f"Invalid sort field '{v}'. Must be one of {article_sort_keys}.")

    return v
  
  @model_validator(mode='after')
  def query_present_for_semantic_and_combined_search(self):
    if (
      (self.search_type == ArticleQueryType.semantic or self.search_type == ArticleQueryType.combined) and (
        self.query is None or self.query.isspace()
      )
    ):
      raise ValueError(f"'query' must not be empty for 'semantic' or 'combined' search.")
    return self

  # limitation of manually combining the text and semantic search results...
  @model_validator(mode='after')
  def paging_disabled_for_semantic_and_combined_search(self):
    if (
      (self.search_type == ArticleQueryType.semantic or self.search_type == ArticleQueryType.combined) and (
        self.page != 0
      )
    ):
      raise ValueError(f"'page' must be 0 for 'semantic' or 'combined' search.")
    return self
   
