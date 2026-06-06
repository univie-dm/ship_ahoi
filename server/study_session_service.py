import os
import redis
import json
import logging

logger = logging.getLogger(__name__)

try:
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    redis_client = redis.StrictRedis.from_url(redis_url, decode_responses=True)
    redis_client.ping()
except Exception as e:
    logger.error(f"Failed to connect to Redis for study session: {e}")
    redis_client = None

def save_parameter_log(session_id: str, log_entry: dict):
    if not redis_client:
        return False
    key = f"study_session:{session_id}:log"
    try:
        redis_client.rpush(key, json.dumps(log_entry))
        redis_client.expire(key, 604800)
        return True
    except Exception as e:
        logger.error(f"Redis save error: {e}")
        return False

def get_session_log(session_id: str):
    if not redis_client:
        return []
    key = f"study_session:{session_id}:log"
    try:
        entries = redis_client.lrange(key, 0, -1)
        return [json.loads(entry) for entry in entries]
    except Exception as e:
        logger.error(f"Redis get error: {e}")
        return []

def clear_session(session_id: str):
    if not redis_client:
        return False
    key = f"study_session:{session_id}:log"
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        return False
