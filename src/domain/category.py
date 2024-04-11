import pydantic


class Category(pydantic.BaseModel):
  id: str
  name: str


class CategoryList(pydantic.BaseModel):
  total_count: int
  categories: list[Category]