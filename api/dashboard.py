"""
仪表盘 API - 学生/管理员首页数据聚合
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.auth import get_current_user
from utils.db import get_db
from models.user import User
from models.access import AccessRecord
from models.visitor import Visitor, VisitorStatus
from models.repair_record import RepairRecord
from models.energy_consumption import EnergyConsumption

router = APIRouter()


@router.get("/stats", summary="仪表盘统计数据")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """根据角色返回不同的统计数据"""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    this_month = now.strftime("%Y-%m")

    data = {
        "user": {
            "id": current_user.id,
            "name": current_user.username,
            "role": current_user.role,
            "dormitory": current_user.dormitory,
        }
    }

    if current_user.role == "admin":
        # ---- 管理员视图 ----
        data["overview"] = {
            "total_users": db.query(User).count(),
            "total_dorms": db.query(User.dormitory).filter(
                User.dormitory.isnot(None), User.dormitory != ""
            ).distinct().count(),
            "today_access": db.query(AccessRecord).filter(
                AccessRecord.access_time >= today_start
            ).count(),
            "today_allowed": db.query(AccessRecord).filter(
                AccessRecord.access_time >= today_start,
                AccessRecord.status == "allowed",
            ).count(),
            "today_denied": db.query(AccessRecord).filter(
                AccessRecord.access_time >= today_start,
                AccessRecord.status == "denied",
            ).count(),
            "pending_visitors": db.query(Visitor).filter(
                Visitor.status == VisitorStatus.PENDING.value
            ).count(),
            "pending_repairs": db.query(RepairRecord).filter(
                RepairRecord.status == "pending"
            ).count(),
            "alarm_energy": db.query(EnergyConsumption).filter(
                EnergyConsumption.alarm == True,
                EnergyConsumption.month == this_month,
            ).count(),
        }

        # 最近通行动态
        recent = (
            db.query(AccessRecord)
            .order_by(AccessRecord.access_time.desc())
            .limit(5)
            .all()
        )
        data["recent_access"] = [
            {
                "username": r.username,
                "dormitory": r.dormitory,
                "status": r.status,
                "time": r.access_time.strftime("%H:%M:%S"),
                "alarm": r.alarm,
            }
            for r in recent
        ]

        # 待办事项
        todos = []
        if data["overview"]["pending_visitors"] > 0:
            todos.append({
                "type": "visitor",
                "text": f"{data['overview']['pending_visitors']} 条访客预约待审核",
                "urgent": True,
            })
        if data["overview"]["pending_repairs"] > 0:
            todos.append({
                "type": "repair",
                "text": f"{data['overview']['pending_repairs']} 条维修申请待处理",
                "urgent": data["overview"]["pending_repairs"] >= 3,
            })
        if data["overview"]["alarm_energy"] > 0:
            todos.append({
                "type": "energy",
                "text": f"{data['overview']['alarm_energy']} 条能耗告警需关注",
                "urgent": True,
            })
        data["todos"] = todos

    else:
        # ---- 学生视图 ----
        dorm = current_user.dormitory or ""

        # 本宿舍本月能耗
        elec = (
            db.query(EnergyConsumption)
            .filter(
                EnergyConsumption.dormitory == dorm,
                EnergyConsumption.month == this_month,
                EnergyConsumption.energy_type == "electricity",
            )
            .first()
        )
        water = (
            db.query(EnergyConsumption)
            .filter(
                EnergyConsumption.dormitory == dorm,
                EnergyConsumption.month == this_month,
                EnergyConsumption.energy_type == "water",
            )
            .first()
        )

        data["energy"] = {
            "month": this_month,
            "electricity": {
                "consumption": elec.consumption if elec else 0,
                "cost": elec.cost if elec else 0,
                "alarm": bool(elec.alarm) if elec else False,
            },
            "water": {
                "consumption": water.consumption if water else 0,
                "cost": water.cost if water else 0,
                "alarm": bool(water.alarm) if water else False,
            },
        }

        # 今日是否已通行
        today_records = (
            db.query(AccessRecord)
            .filter(
                AccessRecord.user_id == current_user.id,
                AccessRecord.access_time >= today_start,
            )
            .all()
        )
        data["today_access"] = {
            "count": len(today_records),
            "last_time": (
                today_records[-1].access_time.strftime("%H:%M")
                if today_records
                else None
            ),
            "status": today_records[-1].status if today_records else None,
        }

        # 我的维修
        my_repairs = (
            db.query(RepairRecord)
            .filter(RepairRecord.user_id == current_user.id)
            .order_by(RepairRecord.created_at.desc())
            .limit(3)
            .all()
        )
        data["my_repairs"] = [
            {
                "id": r.id,
                "title": r.title,
                "status": r.status,
                "created_at": r.created_at.strftime("%m-%d"),
            }
            for r in my_repairs
        ]

        # 我的访客
        my_visitors = (
            db.query(Visitor)
            .filter(Visitor.user_id == current_user.id)
            .order_by(Visitor.created_at.desc())
            .limit(3)
            .all()
        )
        data["my_visitors"] = [
            {
                "id": v.id,
                "name": v.visitor_name,
                "date": v.visit_date.strftime("%m-%d"),
                "status": v.status,
            }
            for v in my_visitors
        ]

    return {"code": 200, "data": data}


@router.get("/energy-chart", summary="能耗图表数据")
def get_energy_chart(
    months: int = Query(default=6, ge=1, le=12, description="查询最近N个月"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回能耗趋势数据，供前端绘制图表"""
    dorm = current_user.dormitory
    if current_user.role == "admin":
        dorm = current_user.dormitory or ""

    # 生成月份列表
    now = datetime.now()
    month_list = []
    for i in range(months - 1, -1, -1):
        m = now.month - i
        y = now.year
        if m <= 0:
            m += 12
            y -= 1
        month_list.append(f"{y}-{m:02d}")

    result = {"months": month_list, "electricity": [], "water": []}

    query = db.query(EnergyConsumption).filter(
        EnergyConsumption.month.in_(month_list)
    )
    if dorm and current_user.role != "admin":
        query = query.filter(EnergyConsumption.dormitory == dorm)
    elif dorm and current_user.role == "admin":
        query = query.filter(EnergyConsumption.dormitory == dorm)

    records = query.all()

    for m in month_list:
        e = next(
            (r for r in records if r.month == m and r.energy_type == "electricity"),
            None,
        )
        w = next(
            (r for r in records if r.month == m and r.energy_type == "water"), None
        )
        result["electricity"].append(
            {
                "consumption": e.consumption if e else 0,
                "cost": e.cost if e else 0,
                "alarm": bool(e.alarm) if e else False,
            }
        )
        result["water"].append(
            {
                "consumption": w.consumption if w else 0,
                "cost": w.cost if w else 0,
                "alarm": bool(w.alarm) if w else False,
            }
        )

    return {"code": 200, "data": result}


@router.get("/notices", summary="公告列表")
def get_notices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """系统公告（目前基于数据动态生成）"""
    now = datetime.now()
    notices = []

    # 待审核访客提醒（管理员）
    if current_user.role == "admin":
        pending = (
            db.query(Visitor).filter(Visitor.status == VisitorStatus.PENDING.value).count()
        )
        if pending:
            notices.append({
                "id": 1,
                "type": "warning",
                "title": "待处理访客预约",
                "content": f"当前有 {pending} 条访客预约等待审核，请及时处理",
                "time": now.strftime("%m-%d %H:%M"),
            })

        repair_pending = (
            db.query(RepairRecord).filter(RepairRecord.status == "pending").count()
        )
        if repair_pending:
            notices.append({
                "id": 2,
                "type": "info",
                "title": "维修待处理",
                "content": f"有 {repair_pending} 条维修申请等待指派处理人员",
                "time": now.strftime("%m-%d %H:%M"),
            })

    # 全体公告
    today_count = (
        db.query(AccessRecord)
        .filter(AccessRecord.access_time >= now.replace(hour=0, minute=0, second=0))
        .count()
    )
    notices.append({
        "id": 3,
        "type": "info",
        "title": "今日通行统计",
        "content": f"今日已有 {today_count} 次通行记录",
        "time": now.strftime("%m-%d %H:%M"),
    })

    # 当月能耗提醒
    this_month = now.strftime("%Y-%m")
    alarms = (
        db.query(EnergyConsumption)
        .filter(EnergyConsumption.month == this_month, EnergyConsumption.alarm == True)
        .count()
    )
    if alarms:
        notices.append({
            "id": 4,
            "type": "warning",
            "title": "能耗告警",
            "content": f"本月有 {alarms} 条能耗告警，请注意节约用水用电",
            "time": now.strftime("%m-%d %H:%M"),
        })

    return {"code": 200, "data": notices}
