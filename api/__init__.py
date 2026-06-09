"""API路由聚合模块"""
from fastapi import APIRouter

from api import auth, user, access, visitor, energy_consumption, repair_record, blacklist, face, dashboard, export

# 创建总路由
api_router = APIRouter()

# 注册子路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(user.router, prefix="/users", tags=["用户管理"])
api_router.include_router(access.router, prefix="/access", tags=["通行管理"])
api_router.include_router(visitor.router, prefix="/visitors", tags=["访客管理"])
api_router.include_router(energy_consumption.router, prefix="/energy", tags=["能耗管理"])
api_router.include_router(repair_record.router, prefix="/repair", tags=["维修管理"])
api_router.include_router(blacklist.router, prefix="/blacklist", tags=["黑名单管理"])
api_router.include_router(face.router, prefix="/face", tags=["人脸管理"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
api_router.include_router(export.router, prefix="/export", tags=["数据导出"])
