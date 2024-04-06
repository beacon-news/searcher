from pydantic import BaseModel, model_validator, field_validator, conint
from datetime import datetime
from enum import Enum
from dto.article_result import ArticleResult
import typing
import types


# article_search_keys = [
#   "id",
#   "categories",
#   "entities",
#   "url",
#   "publish_date",
#   "author",
#   "title",
#   "paragraphs",
# ]

def flatten_model_attributes(d: BaseModel, keys: set, parent_key: str=''):
  """Returns model attributes separated by '.' for nested models, in the 'keys' set."""

  for key, field_info in d.model_fields.items():
    if len(parent_key) == 0:
      key_name = key
    else:
      key_name = parent_key + '.' + key

    if type(field_info.annotation) == type(BaseModel):
      flatten_model_attributes(field_info.annotation, keys, key_name)
    elif type(field_info.annotation) == types.UnionType:
      type_args = typing.get_args(field_info.annotation)
      for t in type_args:
        if type(t) == type(BaseModel):
          flatten_model_attributes(t, keys, key_name)
        else:
          keys.add(key_name)
    else:
      keys.add(key_name)
  
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

  author: str | None = None

  # TODO: add tags to scrape_configs and elastic
  tags: str | None = None

  # ISO8601 date format, see pydantic docs
  date_min: datetime = datetime.fromtimestamp(0)
  date_max: datetime = datetime.now()

  # only applicable to text search
  size: conint(gt=0, lt=30) = 10 # type: ignore

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

  @model_validator(mode='after')
  def some_query_must_be_present(self):
    
    values = [
      self.id,
      self.query,
      self.categories,
      self.author,
      self.tags
    ]
    for v in values:
      if v is not None and v.strip() != "":
        return self
    
    raise ValueError(f"At least one of 'id', 'query', 'categories', 'author' or 'tags' must be specified.")
  
  @model_validator(mode='after')
  def query_present_for_semantic_and_combined_search(self):
    if (
      self.search_type == ArticleQueryType.semantic or self.search_type == ArticleQueryType.combined and (
        self.query is None or self.query.strip() == ""
      )
    ):
      raise ValueError(f"'query' must not be empty for 'semantic' or 'combined' search.")
    return self

  
