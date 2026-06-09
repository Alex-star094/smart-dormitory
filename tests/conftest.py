"""
pytest 配置和共享 Fixtures
运行测试: pytest tests/ -v --cov=. --cov-report=term-missing
"""
import sys
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import Base, get_db
from main import app


# ==================== 测试数据库 ====================

@pytest.fixture(scope="function")
def test_db():
    """每个测试函数使用独立的内存数据库"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # 注入测试数据库到 FastAPI 依赖
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI 测试客户端"""
    with TestClient(app) as c:
        yield c


# ==================== 测试数据工厂 ====================

@pytest.fixture
def admin_token(client, test_db):
    """创建管理员并返回 Token"""
    from crud.user import user_crud, hash_password
    from models.user import User

    user = User(
        student_id="admin001",
        username="测试管理员",
        password=hash_password("admin123"),
        role="admin",
        dormitory="1-101",
    )
    test_db.add(user)
    test_db.commit()

    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "admin001", "password": "admin123", "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return resp.json()["access_token"]


@pytest.fixture
def student_token(client, test_db):
    """创建学生并返回 Token"""
    from crud.user import hash_password
    from models.user import User

    user = User(
        student_id="2024001",
        username="测试学生",
        password=hash_password("123456"),
        role="student",
        dormitory="3-201",
    )
    test_db.add(user)
    test_db.commit()

    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "2024001", "password": "123456", "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return resp.json()["access_token"]
