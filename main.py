"""
智安校园 - 宿舍智能管理系统
FastAPI 应用入口
"""
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException

from api import api_router
from config import settings
from utils.db import engine, Base
from utils.exception import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
from utils.logger import setup_logger
from utils.rate_limiter import rate_limit

# 初始化日志
logger = setup_logger("main")

# 确保控制台支持UTF-8输出
sys.stdout.reconfigure(encoding="utf-8")

# 创建数据库表（开发环境自动建表，生产环境请使用Alembic迁移）
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(
    title="智安校园-宿舍智能管理系统",
    description="后端API服务，支持用户管理、通行管理、访客管理、能耗管理、维修管理等功能",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 跨域配置（允许小程序前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 速率限制（100次/分钟，基于客户端IP）
# 健康检查、文档页不受限
@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    from fastapi import HTTPException

    # 跳过非 API 路径
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:{client_ip}"

    try:
        from utils.redis_utils import redis_client, is_redis_connected
        if is_redis_connected():
            import time
            now = time.time()
            window = 60
            redis_client.zremrangebyscore(key, 0, now - window)
            count = redis_client.zcard(key)
            if count >= settings.RATE_LIMIT_REQUESTS:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={"code": 429, "msg": "请求过于频繁，请稍后重试"},
                )
            redis_client.zadd(key, {str(now): now})
            redis_client.expire(key, window + 10)
    except Exception:
        pass  # Redis 不可用时跳过限流

    return await call_next(request)

# 注册全局异常处理器
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 注册API路由
app.include_router(api_router, prefix="/api/v1")


# 健康检查接口
@app.get("/health", summary="健康检查")
def health_check():
    return {
        "status": "healthy",
        "message": "服务运行正常",
        "version": "2.0.0",
        "modules": ["user", "access", "visitor", "energy", "repair", "blacklist", "face"],
    }


# 启动应用
if __name__ == "__main__":
    import os
    is_dev = os.getenv("ENV", "dev") == "dev"
    # 仅 MySQL 模式支持多 worker；SQLite 必须用 1 worker
    use_mysql = settings.DATABASE_TYPE == "mysql"
    workers = 1 if not use_mysql else 4

    logger.info(f"启动模式: {'开发(单worker+热重载)' if is_dev else '生产'}")
    logger.info(f"数据库: {settings.DATABASE_TYPE.upper()}, Worker数: {workers}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=is_dev,
        log_level="info",
        workers=workers,
    )
