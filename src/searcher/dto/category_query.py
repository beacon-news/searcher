from pydantic import BaseModel, Field, field_validator
from typing import Annotated

class CategoryQuery(BaseModel):
  ids: Annotated[list[str] | None, Field()] = None
  query: Annotated[str | None, Field()] = None

  # pagination
  page: Annotated[int, Field(ge=0)] = 0
  page_size: Annotated[int, Field(ge=1, le=50)] = 10

  @field_validator('ids')
  @classmethod
  def list_not_blank(cls, v: list[str] | None) -> str | None:
    if v is not None:
      new_items = [value for value in v if len(value) > 0 and not value.isspace()]
      if len(new_items) > 100: 
        raise ValueError("list contains too many items")

      return new_items
    return v
