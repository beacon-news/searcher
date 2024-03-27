import redis
import redis.exceptions
import uuid
import time
from random import randint
from utils import log_utils
import threading


class RedisHandler:

  def __init__(self, redis_host, redis_port):
    self.log = log_utils.create_console_logger(
      self.__class__.__name__,
    )
    self.host = redis_host
    self.port = redis_port
    self.__connect()

  def __connect(self):
    # TODO: redis cluster connection
    self.r = redis.Redis(host=self.host, port=self.port, decode_responses=True)

    backoff = randint(500, 1000)
    while not self.r.ping():
      self.log.info(f"redis not ready, waiting {backoff} milliseconds")
      time.sleep(backoff / 1000)
      backoff *= 2

  def consume_stream(self, stream_name, consumer_group, callback, *callback_args):
    
    consumer_name = f"{consumer_group}_{uuid.uuid4().hex}"
    xread_count = 10
    xread_timeout = 10000

    self.__try_create_consumer_group(stream_name, consumer_group)

    # 1. process any pending messages (something happened between consuming and acking a message)
    # 2. try to process any new messages + ack + delete processed messages (cleanup, also prevent trimming)
    # 3. call xautoclaim to claim pending messages

    # try to claim pending messages from other consumers
    autoclaim_exit = threading.Event()
    autoclaim_thread = threading.Thread(
      target=self.__auto_claim, args=(stream_name, consumer_group, consumer_name, autoclaim_exit)
    )
    autoclaim_thread.start()

    self.log.info(f"consumer starting in consumer group {consumer_group}, consumer name: {consumer_name}")
    last_id = "0"
    check_pending_messages = True
    while True:

      if check_pending_messages:
        # consume all pending messages since the last acked one
        id = last_id
      else:
        # only consume new messages
        id = ">"
      
      try:
        messages = self.r.xreadgroup(
          groupname=consumer_group, 
          consumername=consumer_name, 
          streams={stream_name: id}, 
          block=xread_timeout,
          count=xread_count
        )
      except redis.exceptions.ConnectionError:
        # try to connect again
        self.__connect()
      except Exception:
        self.log.exception("unknown error while consuming message")
        return
      except KeyboardInterrupt:
        self.log.info("shutting down consumer, waiting for autoclaim thread to finish")
        autoclaim_exit.set() 
        autoclaim_thread.join()
        return

      if len(messages) == 0:
        self.log.debug(f"{xread_timeout} millis passed, no new messages")
        continue

      # when consuming pending messages, if the length is 0, 
      # we can start consuming new messages (there are no more pending messages)
      # when consuming new messages, the length will never be 0, 
      # we will check pending messages since the last acked message after every new read
      was_pending = check_pending_messages
      check_pending_messages = len(messages[0][1]) != 0 

      # consume the messages, either pending or new
      for message in messages[0][1]:
        try:

          # process the message
          callback(message, *callback_args)
          self.log.debug(f"processed message {message}")

          self.r.xack(stream_name, consumer_group, message[0])
          self.log.debug(f"ack-d message {message}")
          last_id = message[0]

          if was_pending:
            self.log.debug(f"consumed pending message {message}")
          else:
            self.log.debug(f"consumed message {message}")

          # TODO: decide on this
          # do we want to delete?
          # we might only want to regularly trim, or use a capped stream
          # self.r.xdel(stream_name, message[0])
          # self.log.debug(f"deleted message {message}")

        except Exception:
          self.log.exception("error while processing message")


  def __auto_claim(self, stream_name, consumer_group, consumer_name, exit_event: threading.Event): 

    xclaim_idle_time = 1000
    xclaim_count = 10
    claim_interval = 5000

    while True:
      
      # try to claim pending messages from other consumers
      if exit_event.is_set():
        self.log.debug("exiting autoclaim thread")
        break

      try:
        claimed = self.r.xautoclaim(
          stream_name, 
          consumer_group, 
          consumer_name, 
          min_idle_time=xclaim_idle_time, 
          start_id="0-0", 
          count=xclaim_count, 
          justid=True,
        )
        if len(claimed) > 0:
          self.log.debug(f"autoclaimed messages, total pending messages: {len(claimed)}")
      except Exception:
        self.log.exception("error while autoclaiming messages")
      
      time.sleep(claim_interval / 1000)
    

  def __try_create_consumer_group(self, stream_name, consumer_group):
    try:
      self.r.xgroup_create(name=stream_name, groupname=consumer_group, mkstream=True)
      self.log.info(f"created/asserted consumer group {consumer_group} for stream {stream_name}")
    except redis.exceptions.ResponseError as e:
      if "BUSYGROUP" in str(e):
        self.log.info(f"consumer group {consumer_group} already exists")
      else:
        raise
    except Exception:
      self.log.exception(f"error while creating consumer group {consumer_group} for stream {stream_name}")
  