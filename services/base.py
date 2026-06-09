"""
基础 Service 类 — 提供事务管理、缓存、日志等通用能力
"""
import logging
from typing import Optional, Any

from sqlalchemy.orm import Session

logger = logging.getLogger("service")


class BaseService:
    """Service 基类，封装通用业务逻辑模式"""

    def __init__(self):
        self._cache = None

    @property
    def cache(self):
        """懒加载 Redis 缓存"""
        if self._cache is None:
            try:
                from utils.redis_utils import redis_client, is_redis_connected
                if is_redis_connected():
                    self._cache = redis_client
            except Exception:
                pass
        return self._cache

    def get_cache(self, key: str) -> Optional[str]:
        """读取缓存"""
        if self.cache:
            try:
                return self.cache.get(key)
            except Exception:
                return None
        return None

    def set_cache(self, key: str, value: str, ttl: int = 300) -> None:
        """写入缓存（默认5分钟过期）"""
        if self.cache:
            try:
                self.cache.setex(key, ttl, value)
            except Exception:
                pass

    def invalidate_cache(self, pattern: str) -> None:
        """按模式清除缓存"""
        if self.cache:
            try:
                keys = self.cache.keys(pattern)
                if keys:
                    self.cache.delete(*keys)
            except Exception:
                pass

    @staticmethod
    def commit_and_refresh(db: Session, obj: Any) -> Any:
        """提交事务并刷新对象"""
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def rollback_safe(db: Session) -> None:
        """安全回滚"""
        try:
            db.rollback()
        except Exception:
            pass
