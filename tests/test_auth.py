"""
认证模块测试 — JWT Token、密码哈希、权限校验
"""
import pytest
from crud.user import hash_password, verify_password


class TestPasswordHashing:
    """密码哈希与验证"""

    def test_hash_and_verify(self):
        h = hash_password("mypassword123")
        assert h != "mypassword123"  # 不是明文
        assert verify_password("mypassword123", h) is True

    def test_wrong_password_fails(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_different_salts(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # 每次哈希应该不同（随机盐）
        assert verify_password("same", h1)
        assert verify_password("same", h2)


class TestAuthAPI:
    """认证 API 端点测试"""

    def test_login_success(self, client, test_db):
        from crud.user import hash_password
        from models.user import User
        user = User(
            student_id="test001", username="测试",
            password=hash_password("pass123"), role="student"
        )
        test_db.add(user); test_db.commit()

        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "test001", "password": "pass123", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_db):
        from crud.user import hash_password
        from models.user import User
        user = User(
            student_id="test001", username="测试",
            password=hash_password("pass123"), role="student"
        )
        test_db.add(user); test_db.commit()

        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "test001", "password": "wrong", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "nobody", "password": "x", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    def test_protected_route_without_token(self, client):
        resp = client.get("/api/v1/users/profile")
        assert resp.status_code == 401

    def test_profile_with_token(self, client, student_token):
        resp = client.get(
            "/api/v1/users/profile",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["data"]["student_id"] == "2024001"

    def test_student_cannot_access_admin(self, client, student_token):
        resp = client.get(
            "/api/v1/users/list",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

    def test_admin_can_access_user_list(self, client, admin_token):
        resp = client.get(
            "/api/v1/users/list",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 200
