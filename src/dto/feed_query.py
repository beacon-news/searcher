import pydantic


class FeedQuery(pydantic.BaseModel):

  # pagination
  page: pydantic.conint(ge=0) # type: ignore = 0

  # only applicable to text search, semantic search will always limit the returned results
  page_size: pydantic.conint(ge=1, le=30) = 10 # type: ignore

  # return only a subset of an ArticleResult
  # None means return all attributes
  return_attributes: list[str] | None = None  