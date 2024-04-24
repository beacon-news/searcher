from pydantic import BaseModel, field_validator, Field

from typing import Annotated
from datetime import datetime
from .utils import flatten_model_attributes
from .topic_batch_result import TopicBatchResult
from .sort_direction import SortDirection
import typing as t

topic_batch_search_keys = set() 
flatten_model_attributes(TopicBatchResult, topic_batch_search_keys)

topic_batch_sort_keys = set([
  "date_min",
  "date_max",
  "article_count",
  "topic_count",
])

class TopicBatchQuery(BaseModel):
  ids: Annotated[list[str] | None, Field()] = None

  count_min: Annotated[int | None, Field()] = None
  count_max: Annotated[int | None, Field()] = None

  topic_count_min: Annotated[int | None, Field()] = None
  topic_count_max: Annotated[int | None, Field()] = None

  # ISO8601 date format
  date_min: Annotated[datetime | None, Field()] = datetime.fromisoformat('1000-01-01T00:00:00')
  date_max: Annotated[datetime | None, Field()] = datetime.now()
  
  # pagination
  page: Annotated[int, Field(ge=0)] = 0

  # only applicable to text search, semantic search will always limit the returned results
  page_size: Annotated[int, Field(ge=0, le=30)] = 10

  # sorting
  sort_field: Annotated[str | None, Field()] = None
  sort_dir: Annotated[SortDirection | None, Field()] = None

  # return only a subset of an ArticleResult
  # None means return all attributes
  return_attributes: Annotated[t.List[str] | None, Field()] = None


  @field_validator("return_attributes")
  @classmethod
  def validate_return_attributes(cls, v: list[str] | None) -> list[str] | None:
    if v is None or len(v) == 0:
      return None

    for key in v:
      if key not in topic_batch_search_keys:
        raise ValueError(f"Invalid return attribute '{key}'. Must be one of {topic_batch_search_keys}.")

    # all keys are valid, return them
    return v

  @field_validator("sort_field")
  @classmethod
  def is_sortable_key(cls, v: str | None) -> str | None:
    if v is None:
      return None

    if v not in topic_batch_sort_keys:
      raise ValueError(f"Invalid sort field '{v}'. Must be one of {topic_batch_sort_keys}.")

    return v
