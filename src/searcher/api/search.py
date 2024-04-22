from fastapi import APIRouter, Query, Depends
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


# @router.post(
#   "/articles",
#   response_model=ArticleResults,
#   response_model_exclude_none=True,
# )
# async def search_articles(search_options: ArticleQuery | None = ArticleQuery()) -> ArticleResults:
#   return await search_service.search_articles(search_options)

@router.get(
  "/articles",
  response_model=ArticleResults,
  response_model_exclude_none=True,
)
async def search_articles(
  # empty list because None doesn't work properly for OpenAPI here
  ids: Annotated[list[str], Query()] = [],

  query: Annotated[str | None, Query()] = None,
  cateogry_ids: Annotated[list[str] | None, Query()] = None,
  categories: Annotated[str | None, Query()] = None,
  source: Annotated[str | None, Query()] = None,
  author: Annotated[str | None, Query()] = None,

  # ISO8601 date format
  date_min: Annotated[datetime | None, Query()] = datetime.fromisoformat('1000-01-01T00:00:00'),
  date_max: Annotated[datetime | None, Query()] = datetime.now(),

  topic_ids: Annotated[list[str] | None, Query()] = None,
  topic: Annotated[str | None, Query()] = None,

  # pagination
  page: Annotated[int, Query(ge=0)] = 0,

  # only applicable to text search, semantic search will always limit the returned results
  page_size: Annotated[int, Query(ge=0, le=30)] = 10,

  # sorting
  sort_field: Annotated[str | None, Query()] = None,
  sort_dir: Annotated[SortDirection | None, Query()] = None,

  search_type: Annotated[ArticleQueryType | None, Query()] = ArticleQueryType.text,

  # return only a subset of an ArticleResult
  # None or [] means return all attributes
  return_attributes: Annotated[list[str], Query()] = [],
) -> ArticleResults:
  article_query = ArticleQuery(
    ids=ids,
    query=query,
    category_ids=cateogry_ids,
    categories=categories,
    source=source,
    author=author,
    date_min=date_min,
    date_max=date_max,
    topic_ids=topic_ids,
    topic=topic,
    page=page,
    page_size=page_size,
    sort_field=sort_field,
    sort_dir=sort_dir,
    search_type=search_type,
    return_attributes=return_attributes,
  )
  return await search_service.search_articles(article_query)

@router.get(
  "/topics", 
  response_model=TopicResults, 
  response_model_exclude_none=True
)
async def search_topics(
  # empty list because None doesn't work properly for OpenAPI here
  ids: Annotated[list[str], Query()] = [],
  batch_ids: Annotated[list[str], Query()] = [],

  topic: Annotated[str | None, Query()] = None,
  count_min: Annotated[int | None, Query()] = None,
  count_max: Annotated[int | None, Query()] = None,

  # ISO8601 date format
  date_min: Annotated[datetime | None, Query()] = datetime.fromisoformat('1000-01-01T00:00:00'),
  date_max: Annotated[datetime | None, Query()] = datetime.now(),
  
  # pagination
  page: Annotated[int, Query(ge=0)] = 0,

  # only applicable to text search, semantic search will always limit the returned results
  page_size: Annotated[int, Query(ge=0, le=30)] = 10,

  # TODO:
  # sorting
  sort_field: Annotated[str | None, Query()] = None,
  sort_dir: Annotated[SortDirection | None, Query()] = None,

  # return only a subset of an ArticleResult
  # None or [] means return all attributes
  return_attributes: Annotated[list[str], Query()] = [],

) -> TopicResults:
  topic_query = TopicQuery(
    ids=ids,
    batch_ids=batch_ids,
    topic=topic,
    count_min=count_min,
    count_max=count_max,
    date_min=date_min,
    date_max=date_max,
    page=page,
    page_size=page_size,
    sort_field=sort_field,
    sort_dir=sort_dir,
    return_attributes=return_attributes,
  )
  return await search_service.search_topics(topic_query)
    
# @router.post(
#   "/topics", 
#   response_model=TopicResults, 
#   response_model_exclude_none=True
# )
# async def search_topics(topic_query: TopicQuery | None = TopicQuery()) -> TopicResults:
#   return await search_service.search_topics(topic_query)


# @router.post(
#   "/categories", 
#   response_model=CategoryResults, 
#   response_model_exclude_none=True,
# )
# async def search_categories(category_query: CategoryQuery | None = CategoryQuery()) -> CategoryResults:
#   return await search_service.search_categories(category_query)

@router.get(
  "/categories", 
  response_model=CategoryResults, 
  response_model_exclude_none=True,
)
async def search_categories(
  ids: Annotated[list[str], Query()] = [],
  query: Annotated[str | None, Query()] = None,

  # pagination
  page: Annotated[int, Query(ge=0)] = 0,
  page_size: Annotated[int, Query(ge=0, le=50)] = 10,
) -> CategoryResults:
  category_query = CategoryQuery(
    ids=ids,
    query=query,
    page=page,
    page_size=page_size,
  )
  return await search_service.search_categories(category_query)