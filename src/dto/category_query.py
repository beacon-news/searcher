from pydantic import BaseModel, Field, field_validator
from typing import Annotated

class CategoryQuery(BaseModel):
  # ids: list[str] | None  = None
  # names: list[str] | None = None
  top_n: Annotated[int | None, Field(ge=1, le=200)] = None

  # @field_validator('ids', 'names')
  # @classmethod
  # def names_not_blank(cls, v: list[str] | None) -> str | None:
  #   if v is not None:
  #     new_items = [value for value in v if len(value) > 0 and not value.isspace()]
  #     if len(new_items) == 0:
  #       raise ValueError("'ids' and 'names' cannot contain only empty values")
  #     return new_items
  #   return v
