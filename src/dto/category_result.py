import pydantic


class CategoryResult(pydantic.BaseModel):
  name: str
  article_count: int

class CategoryResults(pydantic.BaseModel):
  total: int
  results: list[CategoryResult]
