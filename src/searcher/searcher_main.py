from fastapi import FastAPI
from .api import search


tags_metadata = [
   {
      "name": "Search",
      "description": "Search various objects."
   }
]

app = FastAPI(
  tags_metadata=tags_metadata,
)

app.include_router(router=search.router)
