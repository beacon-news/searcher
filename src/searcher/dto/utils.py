import pydantic
import typing
import types

def flatten_model_attributes(d: pydantic.BaseModel, keys: set, parent_key: str=''):
  """Returns model attributes separated by '.' for nested models, in the 'keys' set."""

  for key, field_info in d.model_fields.items():
    if len(parent_key) == 0:
      key_name = key
    else:
      key_name = parent_key + '.' + key

    if type(field_info.annotation) == type(pydantic.BaseModel):
      flatten_model_attributes(field_info.annotation, keys, key_name)
    elif type(field_info.annotation) == types.UnionType:
      type_args = typing.get_args(field_info.annotation)
      for t in type_args:
        if type(t) == type(pydantic.BaseModel):
          flatten_model_attributes(t, keys, key_name)
        else:
          keys.add(key_name)
    else:
      keys.add(key_name)