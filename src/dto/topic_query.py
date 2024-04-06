from pydantic import BaseModel, model_validator


class TopicQuery(BaseModel):
  id: str | None = None

  # for title and paragraph
  topic: str | None = None

  count_min: int | None = None
  count_max: int | None = None


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
    