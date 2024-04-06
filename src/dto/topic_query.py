from pydantic import BaseModel, model_validator, field_validator
from dto.utils import flatten_model_attributes
from dto.topic_result import TopicResult

topic_search_keys = set() 
flatten_model_attributes(TopicResult, topic_search_keys)


class TopicQuery(BaseModel):
  id: str | None = None

  # for title and paragraph
  topic: str | None = None

  count_min: int | None = None
  count_max: int | None = None

  # return only a subset of a TopicResult
  # None means return all attributes
  return_attributes: list[str] | None = None

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

  @model_validator(mode='after')
  def some_query_must_be_present(self):
    
    values = [
      self.id,
      self.topic,
      self.count_min,
      self.count_max,
    ]
    for v in values:
      if v is not None and str(v).strip() != "":
        return self
    
    raise ValueError(f"At least one of 'id', 'topic', 'count_min', 'count_max' must be specified.")
    