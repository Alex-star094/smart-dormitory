"""
仪表盘 API 测试
"""
import pytest


class TestDashboardAPI:
    """仪表盘接口测试"""

    def test_student_dashboard(self, client, student_token):
        resp = client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200
        d = resp.json()["data"]
        assert d["user"]["role"] == "student"
        assert "energy" in d
        assert "today_access" in d
        assert "my_repairs" in d
        assert "my_visitors" in d

    def test_admin_dashboard(self, client, admin_token):
        resp = client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        d = resp.json()["data"]
        assert d["user"]["role"] == "admin"
        assert "overview" in d
        assert "recent_access" in d
        assert "todos" in d

    def test_energy_chart(self, client, student_token):
        resp = client.get(
            "/api/v1/dashboard/energy-chart?months=3",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200
        d = resp.json()["data"]
        assert len(d["months"]) == 3
        assert "electricity" in d
        assert "water" in d

    def test_notices(self, client, student_token):
        resp = client.get(
            "/api/v1/dashboard/notices",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 200
