import pydantic


class Category(pydantic.BaseModel):
  id: str
  name: str