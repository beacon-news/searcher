from fastapi import APIRouter
from ..dto.article_query import *
from ..dto.article_result import *
from ..dto.topic_query import *
from ..dto.topic_result import *
from ..dto.category_result import *
from ..dto.category_query import *
from ..searcher_setup import search_service


router = APIRouter(
  prefix="/api/v1/search",
  tags=["Search"],
)


@router.post(
  "/articles",
  response_model=ArticleResults,
  response_model_exclude_none=True,
)
async def search_articles(search_options: ArticleQuery | None = ArticleQuery()) -> ArticleResults:
  return await search_service.search_articles(search_options)

    
@router.post(
  "/topics", 
  response_model=TopicResults, 
  response_model_exclude_none=True
)
async def search_topics(topic_query: TopicQuery | None = TopicQuery()) -> TopicResults:
  return await search_service.search_topics(topic_query)


@router.post(
  "/categories", 
  response_model=CategoryResults, 
  response_model_exclude_none=True,
)
async def search_categories(category_query: CategoryQuery | None = CategoryQuery()) -> CategoryResults:
  return await search_service.search_categories(category_query)