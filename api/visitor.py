from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi import Body
from typing import List, Optional
from datetime import datetime, date
from crud.visitor import visitor_crud
from crud.blacklist import blacklist_crud
from api.auth import get_current_user, require_admin
from utils.db import get_db
from models.visitor import Visitor, VisitorStatus
from models.user import User
from utils.id_card_utils import is_valid_id_card, normalize_id_card
from pydantic import BaseModel
router = APIRouter()

# 新增：定义JSON请求体模型（字段名与前端传递的key完全一致）
class VisitorCreate(BaseModel):
    visitor_name: str  # 对应前端visitorData.visitor_name
    id_card: str       # 对应前端visitorData.id_card
    visit_date: str    # 对应前端visitorData.visit_date（YYYY-MM-DD）
    visit_reason: str  # 对应前端visitorData.visit_reason

@router.post("", summary="创建访客预约（仅需输入日期，有效时段9:00-20:00）")
def create_visitor(
    # 核心修改：通过Body解析JSON请求体，依赖VisitorCreate模型校验
    obj_in: VisitorCreate = Body(..., description="访客预约信息（JSON格式）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """学生创建访客预约（仅选日期，有效时段为当天9:00-20:00）"""
    # 从模型中提取参数（与原逻辑一致，仅修改参数来源）
    visitor_name = obj_in.visitor_name
    id_card = obj_in.id_card
    visit_date = obj_in.visit_date
    visit_reason = obj_in.visit_reason

    # 1. 身份证号校验与规范化（原逻辑不变）
    is_valid, error_msg = is_valid_id_card(id_card)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"身份证号验证失败：{error_msg}"
        )
    normalized_id_card = normalize_id_card(id_card)

    # 2. 黑名单检查（原逻辑不变）
    blacklist_record = blacklist_crud.check_in_blacklist(
        db, id_card=normalized_id_card, name=visitor_name
    )
    if blacklist_record:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"该访客已被禁止预约，原因: {blacklist_record.reason}"
        )

    # 3. 日期解析与校验（原逻辑不变）
    try:
        visit_date_obj = datetime.strptime(visit_date, "%Y-%m-%d").date()
        if visit_date_obj < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="预约日期不能早于当前日期"
            )
        visit_datetime = datetime.combine(visit_date_obj, datetime.min.time())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="日期格式错误，仅支持YYYY-MM-DD（如2025-12-25）"
        )

    # 4. 创建预约（原逻辑不变）
    try:
        current_time = datetime.now().strftime("%H:%M:%S")
        visit_datetime_str = f"{visit_date} {current_time}"
        visit_datetime = datetime.strptime(visit_datetime_str, "%Y-%m-%d %H:%M:%S")
        visitor = visitor_crud.create(db, obj_in={
            "user_id": current_user.id,
            "visitor_name": visitor_name,
            "id_card": normalized_id_card,
            "visit_date": visit_datetime,
            "visit_reason": visit_reason,
            "status": VisitorStatus.PENDING
        })
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # 返回响应（原逻辑不变）
    return {
        "code": 200,
        "msg": f"访客预约创建成功，等待管理员审核！预约日期：{visit_date}，当日有效时段：9:00-20:00",
        "data": {
            "visitor_id": visitor.id,
            "visit_date": visit_date,
            "valid_time_range": "9:00-20:00",
            "current_status": visitor.status
        }
    }

# 查询我的预约：仅返回日期，标注有效时段
@router.get("/my", summary="查询我的访客预约")
def get_my_visitors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    visitors = visitor_crud.get_by_user_id(db, user_id=current_user.id)
    return {
        "code": 200,
        "data": {
            "visitors": [
                {
                    "id": v.id,
                    "visitor_name": v.visitor_name,
                    "id_card": v.id_card,
                    "visit_date": v.visit_date.strftime("%Y-%m-%d"),  # 仅显示日期
                    "valid_time_range": "9:00-20:00",  # 说明有效时段
                    "visit_reason": v.visit_reason,
                    "status": v.status,
                    "approve_note": v.approve_note
                } for v in visitors
            ]
        }
    }

# 示例：记录访客进入时间时校验时段
@router.post("/{visitor_id}/enter", summary="记录访客进入时间")
def record_enter_time(
    visitor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    visitor = visitor_crud.get(db, id=visitor_id)
    if not visitor:
        raise HTTPException(status_code=404, detail="访客预约不存在")
    
    # 获取当前时间
    now = datetime.now()
    # 校验：进入时间需在预约日期的9:00-20:00之间
    if now.date() != visitor.visit_date.date():
        raise HTTPException(status_code=400, detail="仅可在预约日期进入")
    if not (9 <= now.hour <= 20):
        raise HTTPException(status_code=400, detail="仅可在预约日9:00-20:00之间进入")
    
    # 记录进入时间
    visitor.enter_time = now
    db.commit()
    return {"code":200, "msg":"记录进入时间成功"}

# 管理员审核接口：仅返回日期，标注有效时段
@router.put("/{visitor_id}/approve", summary="管理员审核访客预约")
def approve_visitor(
    visitor_id: int,
    approval_status: str = Body(..., description="审核状态：approved/rejected"),
    approve_note: Optional[str] = Body(None, description="审核备注"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    try:
        new_status = VisitorStatus(approval_status.lower())
        if new_status not in [VisitorStatus.APPROVED, VisitorStatus.REJECTED]:
            raise ValueError()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"参数错误：{str(e)}，可选值：['approved', 'rejected']"
        )
    
    visitor = visitor_crud.update_approval(
        db,
        visitor_id=visitor_id,
        status=new_status,
        approver_id=current_user.id,
        approve_note=approve_note
    )
    
    if not visitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="访客预约不存在"
        )
    
    return {
        "code": 200,
        "msg": f"审核成功，状态更新为{new_status.value}",
        "data": {
            "visitor_id": visitor.id,
            "visit_date": visitor.visit_date.strftime("%Y-%m-%d"),  # 仅显示日期
            "valid_time_range": "9:00-20:00",
            "status": visitor.status
        }
    }

# 管理员查询所有预约：仅返回日期，标注有效时段
@router.get("/list", summary="管理员获取所有访客预约")
def get_visitor_list(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    visitor_status = None
    if status:
        try:
            visitor_status = VisitorStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态类型，可选值：{[s.value for s in VisitorStatus]}"
            )
    
    query = db.query(Visitor)
    if visitor_status:
        query = query.filter(Visitor.status == visitor_status.value.lower())
    visitors = query.offset(skip).limit(limit).all()
    
    return {
        "code": 200,
        "data": {
            "total": len(visitors),
            "visitors": [
                {
                    "id": v.id,
                    "visitor_name": v.visitor_name,
                    "id_card": v.id_card,
                    "visit_date": v.visit_date.strftime("%Y-%m-%d"),  
                    "valid_time_range": "9:00-20:00",  # 说明有效时段
                    "visit_reason": v.visit_reason,
                    "status": v.status,
                    "booker": v.booker.username,
                    "booker_student_id": v.booker.student_id,
                    "approver": v.approver.username if v.approver else None,
                    "approve_note": v.approve_note
                } for v in visitors
            ]
        }
    }