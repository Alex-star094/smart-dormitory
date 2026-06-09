"""
API速率限制中间件 - 基于Redis的简单限流
如果Redis不可用，降级为内存限流
"""
import time
import logging
from collections import defaultdict
from typing import Tuple

from fastapi import Request, HTTPException, status

logger = logging.getLogger("rate_limiter")

# 内存限流存储（Redis不可用时的降级方案）
_memory_store: dict[str, list[float]] = defaultdict(list)


def _clean_old_requests(key: str, window: int) -> None:
    """清理窗口外的旧请求时间戳"""
    now = time.time()
    _memory_store[key] = [t for t in _memory_store[key] if now - t < window]


def rate_limit(
    max_requests: int = 100,
    window_seconds: int = 60,
) -> callable:
    """
    速率限制依赖注入

    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口（秒）

    Returns:
        FastAPI 依赖函数
    """

    async def _rate_limiter(request: Request) -> None:
        # 健康检查接口不限流
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return

        # 使用客户端IP作为限流key
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}"

        # 尝试使用Redis限流
        try:
            from utils.redis_utils import redis_client, is_redis_connected

            if is_redis_connected():
                now = time.time()
                # 使用有序集合实现滑动窗口
                redis_client.zremrangebyscore(key, 0, now - window_seconds)
                count = redis_client.zcard(key)
                if count >= max_requests:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"请求过于频繁，请{window_seconds}秒后重试",
                    )
                redis_client.zadd(key, {str(now): now})
                redis_client.expire(key, window_seconds + 10)
                return
        except Exception:
            pass  # Redis不可用时降级为内存限流

        # 内存限流（降级方案）
        _clean_old_requests(key, window_seconds)
        if len(_memory_store[key]) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，请{window_seconds}秒后重试",
            )
        _memory_store[key].append(time.time())

    return _rate_limiter
