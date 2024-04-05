

d = {
  'a': {
    'b': {
      'c': {
        'd': 1
      },
      'e': 3
    },
    'f': 4
  },
  'e': 2,
  'g': 5
}

def flatten_rec(d: dict, new_dict: dict, parent_key: str=''):
  for key, value in d.items():
    if len(parent_key) == 0:
      key_name = key
    else:
      key_name = parent_key + '.' + key

    if isinstance(value, dict):
      flatten_rec(value, new_dict, key_name)
    else:
      new_dict[key_name] = value


def flatten(d: dict) -> dict:

  new_dict = {}
  flatten_rec(d, new_dict)
  return new_dict


def flatten_dict_keys(d: dict, key_list: list, parent_key: str=''):
  for key, value in d.items():
    if len(parent_key) == 0:
      key_name = key
    else:
      key_name = parent_key + '.' + key

    if isinstance(value, dict):
      flatten_dict_keys(value, key_list, key_name)
    else:
      key_list.append(key_name)

import json

# n = flatten(d)

# n = {}
# flatten_rec(d, n)

# l = []
# flatten_dict_keys(d, l)

# print(json.dumps(n, indent=2))
# print(l)

from dto.article_query import *
from dto.article_result import *
import pydantic as pd

import typing
import types

def fdk(d: dict, key_list: list, parent_key: str=''):
  for key, field_info in d.items():
    if len(parent_key) == 0:
      key_name = key
    else:
      key_name = parent_key + '.' + key

    print(key, field_info.annotation, type(field_info.annotation))

    # print(field_info.annotation, hasattr(field_info.annotation, 'model_fields'))

    if type(field_info.annotation) == type(pd.BaseModel):
      fdk(field_info.annotation.model_fields, key_list, key_name)
    elif type(field_info.annotation) == types.UnionType:
      type_args = typing.get_args(field_info.annotation)
      for t in type_args:
        if type(t) == type(pd.BaseModel):
          fdk(t.model_fields, key_list, key_name)
        else:
          key_list.append(key_name)
    else:
      # assume every other thing is a primitive type
      key_list.append(key_name)

m = ArticleResult.model_fields
o = ArticleResult

import typing as t

# ArticleResult.model_dump()

# r = ArticleResult()
# print(hasattr(r, 'id'))
# print(hasattr(ArticleResult, 'id'))

l = []
fdk(ArticleResult.model_fields, l)
print(l)

print(type(pd.BaseModel))
for k in m:
  # print(k, type(m[k]), m[k].annotation, type(m[k].annotation)) 
  print(m[k].annotation, type(m[k].annotation)) 

  a = t.get_args(m[k].annotation)
  print(a)
  for i in a:
    print(i, type(i) == type(pd.BaseModel))
    if type(i) == type(pd.BaseModel):
      print(i.model_fields)

  # print(isinstance(m[k].annotation, type(pd.BaseModel)))
  # print(type(m[k].annotation) == type(pd.BaseModel))

  # print(m[k].alias)
  # print(hasattr(ArticleResult, 'id'))



  
  # print(m[k].annotation)
  if hasattr(m[k], 'model_fields'):
    print(k, m[k].model_fields)
  
  # print(issubclass(getattr(o, k), pd.BaseModel))

  # print(m[k].annotation, isinstance(m[k], pd.BaseModel))


