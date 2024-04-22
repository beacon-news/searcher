from pydantic import BaseModel


# TODO: change 'dict' fields to have proper types

class TopicResult(BaseModel):
  id: str | None = None

  # info about the batch the topic is a part of
  batch_id: str | None = None
  batch_query: dict | None = None

  # topic name
  topic: str | None = None

  # number of articles in the topic
  count: int | None = None
  representative_articles: list[dict] | None = None


class TopicResults(BaseModel):
  total: int
  results: list[TopicResult]