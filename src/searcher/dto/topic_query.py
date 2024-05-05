from pydantic import BaseModel, field_validator, Field

from typing import Annotated
from datetime import datetime
from .utils import flatten_model_attributes
from .topic_result import TopicResult
from .sort_direction import SortDirection

topic_search_keys = set() 
flatten_model_attributes(TopicResult, topic_search_keys)

topic_sort_keys = set([
  "date_min",
  "date_max",
  "count",
])

class TopicQuery(BaseModel):
  ids: Annotated[list[str] | None, Field()] = None

  batch_ids: Annotated[list[str] | None, Field()] = None

  topic: Annotated[str | None, Field()] = None

  count_min: Annotated[int | None, Field()] = None
  count_max: Annotated[int | None, Field()] = None

  # ISO8601 date format
  date_min: Annotated[datetime | None, Field()] = datetime.fromisoformat('1000-01-01T00:00:00')
  date_max: Annotated[datetime | None, Field(default_factory=datetime.now)]
  
  # pagination
  page: Annotated[int, Field(ge=0)] = 0

  # only applicable to text search, semantic search will always limit the returned results
  page_size: Annotated[int, Field(ge=0, le=30)] = 10

  # sorting
  sort_field: Annotated[str | None, Field()] = None
  sort_dir: Annotated[SortDirection | None, Field()] = None

  # return only a subset of an ArticleResult
  # None means return all attributes
  return_attributes: Annotated[list[str] | None, Field()] = None


  @field_validator("return_attributes")
  @classmethod
  def validate_return_attributes(cls, v: list[str] | None) -> list[str] | None:
    if v is None or len(v) == 0:
      return None

    for key in v:
      if key not in topic_search_keys:
        raise ValueError(f"Invalid return attribute '{key}'. Must be one of {topic_search_keys}.")

    # all keys are valid, return them
    return v

  @field_validator("sort_field")
  @classmethod
  def is_sortable_key(cls, v: str | None) -> str | None:
    if v is None:
      return None

    if v not in topic_sort_keys:
      raise ValueError(f"Invalid sort field '{v}'. Must be one of {topic_sort_keys}.")

    return v

  # @model_validator(mode='after')
  # def some_query_must_be_present(self):
    
  #   values = [
  #     self.id,
  #     self.topic,
  #     self.count_min,
  #     self.count_max,
  #     self.date_min,
  #     self.date_max,
  #   ]
  #   for v in values:
  #     if v is not None and str(v).strip() != "":
  #       return self
    
  #   keys = [
  #     "id",
  #     "topic",
  #     "count_min",
  #     "count_max",
  #     "date_min",
  #     "date_max",
  #   ]
    
  #   raise ValueError(f"At least one of {keys} must be specified.")
    