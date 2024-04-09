from pydantic import BaseModel, model_validator, field_validator, conint
from datetime import datetime
from enum import Enum
from dto.article_result import ArticleResult
from dto.utils import flatten_model_attributes

  
# find out the flattened keys of ArticleResult
article_search_keys = set()
flatten_model_attributes(ArticleResult, article_search_keys)


# model classes
class ArticleQueryType(str, Enum):
  text = "text"
  semantic = "semantic"
  combined = "combined"


class ArticleQuery(BaseModel):
  id: str | None = None

  # for title and paragraph
  query: str | None = None

  categories: str | None = None

  source: str | None = None

  author: str | None = None

  # ISO8601 date format, see pydantic docs
  date_min: datetime = datetime.fromisoformat('1000-01-01T00:00:00')
  date_max: datetime = datetime.now()

  topic_ids: list[str] | None = None
  topic: str | None = None

  # pagination
  page: conint(ge=0) = 0# type: ignore = 0

  # only applicable to text search, semantic search will always limit the returned results
  page_size: conint(ge=1, le=30) = 10 # type: ignore

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


  # if nothing is present, simply returns the most recent articles...

  # @model_validator(mode='after')
  # def some_query_must_be_present(self):
    
  #   str_values = [
  #     self.id,
  #     self.query,
  #     self.categories,
  #     self.source,
  #     self.author,
  #     self.topic,
  #   ]
  #   for v in str_values:
  #     if v is not None and v.strip() != "":
  #       return self
    
  #   list_values = [
  #     self.topic_ids,
  #   ]
  #   for v in list_values:
  #     if v is not None and len(v) > 0:
  #       return self
      
  #   keys = [
  #     "id",
  #     "query",
  #     "categories",
  #     "source",
  #     "author",
  #     "topic",
  #     "topic_ids",
  #   ]
    
  #   raise ValueError(f"At least one of {keys} must be specified.")
  
  @model_validator(mode='after')
  def query_present_for_semantic_and_combined_search(self):
    if (
      (self.search_type == ArticleQueryType.semantic or self.search_type == ArticleQueryType.combined) and (
        self.query is None or self.query.strip() == ""
      )
    ):
      raise ValueError(f"'query' must not be empty for 'semantic' or 'combined' search.")
    return self

  
