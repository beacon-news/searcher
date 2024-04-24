from pydantic import BaseModel
from datetime import datetime


# TODO: change 'dict' fields to have proper types

class TopicBatchResult(BaseModel):
  id: str | None = None

  # query used to generate the batch
  query: dict | None = None

  # number of articles in the batch
  article_count: int | None = None

  topic_count: int | None = None

  create_time: datetime | None = None


class TopicBatchResults(BaseModel):
  total: int
  results: list[TopicBatchResult]