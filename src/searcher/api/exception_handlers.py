from pydantic import ValidationError
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from ..dto.exceptions import QueryValidationException


# TODO: this masks internal errors, returns them as 422 errors, which should be a 500

# # for pydantic errors
# def handle_validation_errors(request: Request, e: ValidationError) -> JSONResponse:
#   errors = [{
#     "loc": err["loc"],
#     "msg": err["msg"],
#     "input": err["input"],
#   } for err in e.errors()]

#   return JSONResponse(
#     status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#     content=jsonable_encoder({"detail": errors})
#   )

def handle_query_validation_errors(request: Request, e: QueryValidationException) -> JSONResponse:
  errors = [{
    "msg": e.message
  }]

  return JSONResponse(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    content=jsonable_encoder({"detail": errors})
  )

# for FastAPI-specific errors
def handle_request_validation_errors(request: Request, e: RequestValidationError) -> JSONResponse:
  errors = [{
    "loc": err["loc"],
    "msg": err["msg"],
    "input": err["input"],
  } for err in e.errors()]

  return JSONResponse(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    content=jsonable_encoder({"detail": errors})
  )

handlers = [
  # (ValidationError, handle_validation_errors),
  (QueryValidationException, handle_query_validation_errors),
  (RequestValidationError, handle_request_validation_errors),
]
