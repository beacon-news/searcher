import pydantic


class CategoryResult(pydantic.BaseModel):
  id: str 
  name: str
  article_count: int | None = None


class CategoryResults(pydantic.BaseModel):
  total: int
  results: list[CategoryResult]
