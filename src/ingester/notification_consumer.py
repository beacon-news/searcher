from abc import ABC, abstractmethod
from ingester.redis_handler import RedisHandler
from typing import Callable
import json

class AsyncNotificationConsumer(ABC):

  @abstractmethod
  async def consume(self, callback: Callable[[dict], None], *callback_args) -> None:
    raise NotImplementedError
  

class RedisNotificationConsumer(AsyncNotificationConsumer):

  def __init__(self, *args, stream_name, consumer_group, **kwargs):
    self.rh = RedisHandler(*args, **kwargs)
    self.stream_name = stream_name
    self.consumer_group = consumer_group
  
  async def consume(self, callback, *callback_args) -> None:

    async def message_extractor_wrapper(message: tuple[str, list[str]]):
      msg = json.loads(message[1]["done"])
      await callback(msg, *callback_args)
      
    await self.rh.consume_stream(self.stream_name, self.consumer_group, message_extractor_wrapper)