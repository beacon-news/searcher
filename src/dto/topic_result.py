from pydantic import BaseModel


class TopicResult(BaseModel):
  id: str | None = None

  # the query used to get the articles which created this topic
  query: dict | None = None

  # topic name
  topic: str | None = None

  # number of articles in the topic
  count: int | None = None
  representative_articles: list[dict] | None = None


class TopicResults(BaseModel):
  results: list[TopicResult]