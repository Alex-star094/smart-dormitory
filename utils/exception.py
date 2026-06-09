"""
全局异常处理模块
"""
import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException

logger = logging.getLogger("exception_handler")


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求参数验证错误处理（400）"""
    errors = [err["msg"] for err in exc.errors()]
    logger.warning(f"请求参数验证失败: {errors}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": 400,
            "msg": "请求参数错误，请检查输入格式",
            "detail": errors,
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理（如401未授权、404未找到等）"""
    logger.warning(f"HTTP异常 [{exc.status_code}]: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "msg": exc.detail,
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理（500 - 不暴露内部错误详情）"""
    logger.error(f"未处理的异常: {type(exc).__name__}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "msg": "服务器内部错误，请稍后重试",
        },
    )
