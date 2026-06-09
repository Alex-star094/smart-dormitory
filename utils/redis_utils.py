"""
Redis工具模块 - 提供Redis连接和缓存操作
"""
import redis
import logging

from config import settings

logger = logging.getLogger("redis_utils")

# 创建Redis客户端
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
)


def is_redis_connected() -> bool:
    """检查Redis连接状态"""
    try:
        return redis_client.ping()
    except Exception as e:
        logger.warning(f"Redis连接失败：{str(e)}")
        return False


# 初始化检查
if not is_redis_connected():
    logger.warning("Redis服务未连接，部分功能可能不可用")
