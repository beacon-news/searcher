import pydantic


class CategoryResult(pydantic.BaseModel):
  id: str 
  name: str


class CategoryResults(pydantic.BaseModel):
  total: int
  results: list[CategoryResult]
