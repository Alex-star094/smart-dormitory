"""
Service 层 — 业务逻辑核心
API 层 → Service 层 → CRUD 层
"""
from services.user_service import UserService
from services.dashboard_service import DashboardService

user_service = UserService()
dashboard_service = DashboardService()
