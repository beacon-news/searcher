import pydantic


class CategoryQuery(pydantic.BaseModel):
  size: pydantic.conint(ge=0, le=50) # type: ignore
