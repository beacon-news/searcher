from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .api import search
from .api import exception_handlers
from .searcher_setup import (
  CORS_ALLOWED_HEADERS, 
  CORS_ALLOWED_METHODS,
  CORS_ALLOWED_ORIGINS,
  CORS_ALLOW_CREDENTIALS
)


tags_metadata = [
   {
      "name": "Search",
      "description": "Search various objects."
   }
]

# creates db indices and closes the async db when the app closes
@asynccontextmanager
async def ensure_db(app: FastAPI):
  from .searcher_setup import repository
  # startup
  await repository.assert_indices()

  yield

  # shutdown
  await repository.close()


app = FastAPI(
  tags_metadata=tags_metadata,
  lifespan=ensure_db,
)

for h in exception_handlers.handlers:
  app.add_exception_handler(*h)

app.add_middleware(
  CORSMiddleware,
  allow_origins=CORS_ALLOWED_ORIGINS,
  allow_credentials=CORS_ALLOW_CREDENTIALS,
  allow_methods=CORS_ALLOWED_METHODS,
  allow_headers=CORS_ALLOWED_HEADERS,
)

app.include_router(router=search.router)
