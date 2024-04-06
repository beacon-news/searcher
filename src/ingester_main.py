import os
import asyncio
from ingester.notification_consumer import *
from ingester.analyzer_repository import *
from searcher.src.repository.elasticsearch_repository import *
from utils import log_utils
from dotenv import load_dotenv

load_dotenv()

def check_env(name: str, default=None) -> str:
  value = os.environ.get(name, default)
  if value is None:
    raise ValueError(f'{name} environment variable is not set')
  return value

REDIS_HOST = check_env('REDIS_HOST', 'localhost')
REDIS_PORT = int(check_env('REDIS_PORT', 6379))

# REDIS_CONSUMER_GROUP = check_env('REDIS_CONSUMER_GROUP', 'searcher_api')
# REDIS_STREAM_NAME = check_env('REDIS_STREAM_NAME', 'analyzer_articles')

MONGO_HOST = check_env('MONGO_HOST', 'localhost')
MONGO_PORT = int(check_env('MONGO_PORT', 27017))
MONGO_DB_ANALYZER = check_env('MONGO_DB_ANALYZER', 'analyzer')
MONGO_COLLECTION_ANALYZER = check_env('MONGO_COLLECTION_ANALYZER', 'analyzed_articles')

ELASTIC_USER = check_env('ELASTIC_USER', 'elastic')
ELASTIC_PASSWORD = check_env('ELASTIC_PASSWORD')
ELASTIC_CONN = check_env('ELASTIC_HOST', 'https://localhost:9200')
ELASTIC_CA_PATH = check_env('ELASTIC_CA_PATH', '../certs/_data/ca/ca.crt')
ELASTIC_TLS_INSECURE = bool(check_env('ELASTIC_TLS_INSECURE', False))

log = log_utils.create_console_logger("Ingester")

analyzer_repo = MongoAnalyzerRepository(
  MONGO_HOST,
  MONGO_PORT,
  db_name=MONGO_DB_ANALYZER,
  collection_name=MONGO_COLLECTION_ANALYZER,
)

es = ElasticsearchRepository(
  ELASTIC_CONN, 
  ELASTIC_USER, 
  ELASTIC_PASSWORD, 
  ELASTIC_CA_PATH, 
  not ELASTIC_TLS_INSECURE
)

# TODO: consolidate data formats
async def process_notification(ids: list[str]): 

  # get the scraped batch
  docs = analyzer_repo.get_article_batch(ids) 
  if len(docs) == 0:
    log.warning(f"no documents found in analyzer batch, exiting")
    return

  # ingest the batch
  await es.store_batch(docs) 

  log.info(f"stored articles in elasticsearch")

async def main():
  await es.assert_articles_index()

  await RedisNotificationConsumer(
    REDIS_HOST,
    REDIS_PORT,
    stream_name="analyzer_articles",
    consumer_group="searcher_api"
  ).consume(process_notification)

  
if __name__ == "__main__":
  asyncio.run(main())
