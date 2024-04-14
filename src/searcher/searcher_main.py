from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import search
from .searcher_setup import CORS_ALLOWED_HEADERS, CORS_ALLOWED_METHODS, CORS_ALLOWED_ORIGINS, CORS_ALLOW_CREDENTIALS


tags_metadata = [
   {
      "name": "Search",
      "description": "Search various objects."
   }
]

app = FastAPI(
  tags_metadata=tags_metadata,
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=CORS_ALLOWED_ORIGINS,
  allow_credentials=CORS_ALLOW_CREDENTIALS,
  allow_methods=CORS_ALLOWED_METHODS,
  allow_headers=CORS_ALLOWED_HEADERS,
)

app.include_router(router=search.router)
