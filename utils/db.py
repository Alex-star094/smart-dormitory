"""
数据库连接模块 - 配置SQLAlchemy引擎和会话管理
支持 SQLite（本地开发）和 MySQL（生产环境）

SQLite 并发策略:
  - WAL 日志模式：允许多个读操作与一个写操作同时进行
  - 连接池：QueuePool(10+20) 支持多 worker 并发
  - busy_timeout=5s：写锁等待而非立即失败
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

if settings.DATABASE_TYPE == "sqlite":
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        """每次新连接时设置 SQLite 优化参数"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA cache_size=-20000")  # 20MB
        cursor.close()

else:
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL + "?ssl_disabled=True"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        echo=False,
    )

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 模型基类
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：每个请求获取独立会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
