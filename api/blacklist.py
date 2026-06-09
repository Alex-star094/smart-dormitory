from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel  # 新增导入
from crud.blacklist import blacklist_crud
from crud.user import user_crud
from api.auth import get_current_user, require_admin
from utils.db import get_db
from models.blacklist import BlacklistRecord, BlacklistType, BlacklistReason, BlacklistStatus
from models.user import User
from utils.id_card_utils import is_valid_id_card, normalize_id_card

router = APIRouter()

# 新增：添加黑名单的JSON请求体模型
class BlacklistCreate(BaseModel):
    name: str
    blacklist_type: str
    reason: str
    description: Optional[str] = None
    student_id: Optional[str] = None
    id_card: Optional[str] = None
    effective_to: Optional[str] = None

# 新增：更新黑名单状态的JSON请求体模型
class BlacklistStatusUpdate(BaseModel):
    status: str
    removal_reason: Optional[str] = None

@router.post("", summary="添加黑名单记录")
def add_to_blacklist(
    # 核心修改：通过Body解析JSON请求体
    obj_in: BlacklistCreate = Body(..., description="黑名单添加信息（JSON格式）"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理员添加黑名单记录"""
    # 从模型提取参数
    name = obj_in.name
    blacklist_type = obj_in.blacklist_type
    reason = obj_in.reason
    description = obj_in.description
    student_id = obj_in.student_id
    id_card = obj_in.id_card
    effective_to = obj_in.effective_to

    # 验证参数（原有逻辑不变）
    try:
        type_enum = BlacklistType(blacklist_type)
        reason_enum = BlacklistReason(reason)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"参数错误: {str(e)}"
        )
    
    # 验证学生是否存在（原有逻辑不变）
    if student_id:
        user = user_crud.get_by_student_id(db, student_id=student_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="学号对应的用户不存在"
            )
        name = name or user.username
    
    # 身份证号校验与规范化（原有逻辑不变）
    normalized_id_card = None
    if id_card:
        is_valid, error_msg = is_valid_id_card(id_card)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"身份证号验证失败：{error_msg}"
            )
        normalized_id_card = normalize_id_card(id_card)
    
    # 确保至少有一个身份标识（原有逻辑不变）
    if not student_id and not normalized_id_card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须填写学号或身份证号中的至少一项"
        )
    
    # 解析失效时间（原有逻辑不变）
    effective_to_dt = None
    if effective_to:
        try:
            effective_to_dt = datetime.fromisoformat(effective_to)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="失效时间格式错误，应为 ISO 格式"
            )
    
    # 创建黑名单记录（原有逻辑不变）
    record = blacklist_crud.create(db, obj_in={
        "student_id": student_id,
        "id_card": normalized_id_card,
        "name": name,
        "blacklist_type": type_enum,
        "reason": reason_enum,
        "description": description,
        "effective_to": effective_to_dt,
        "created_by": current_user.id
    })
    
    return {
        "code": 200,
        "msg": "黑名单添加成功",
        "data": {"record_id": record.id}
    }

@router.get("/active", summary="获取生效中的黑名单")
def get_active_blacklist(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取所有生效中的黑名单记录"""
    records = blacklist_crud.get_active_records(db, skip=skip, limit=limit)
    
    return {
        "code": 200,
        "data": {
            "total": len(records),
            "records": [
                {
                    "id": r.id,
                    "name": r.name,
                    "student_id": r.student_id,
                    "id_card": r.id_card,
                    "blacklist_type": r.blacklist_type,
                    "reason": r.reason,
                    "description": r.description,
                    "status": r.status,
                    "effective_from": r.effective_from,
                    "effective_to": r.effective_to,
                    "created_at": r.created_at
                } for r in records
            ]
        }
    }

@router.put("/{record_id}/status", summary="更新黑名单状态")
def update_blacklist_status(
    record_id: int,
    # 核心修改：通过Body解析JSON请求体
    obj_in: BlacklistStatusUpdate = Body(..., description="状态更新信息（JSON格式）"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理员更新黑名单状态（移除或恢复）"""
    # 从模型提取参数
    status = obj_in.status
    removal_reason = obj_in.removal_reason

    # 验证状态合法性（原有逻辑不变）
    try:
        status_enum = BlacklistStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的状态，可选值：{[s.value for s in BlacklistStatus]}"
        )
    
    # 移除时必须填写原因（补充校验）
    if status_enum == BlacklistStatus.REMOVED and not (removal_reason and removal_reason.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="移除黑名单必须填写移除原因"
        )
    
    # 更新状态（原有逻辑不变）
    record = blacklist_crud.update_status(
        db, 
        record_id=record_id,
        status=status_enum,
        removed_by=current_user.id if status_enum == BlacklistStatus.REMOVED else None,
        removal_reason=removal_reason
    )
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="黑名单记录不存在"
        )
    
    return {
        "code": 200,
        "msg": f"黑名单状态已更新为{status_enum.value}",
        "data": {"record_id": record.id, "status": record.status}
    }

@router.post("/check", summary="检查是否在黑名单中")
def check_blacklist(
    student_id: Optional[str] = None,
    id_card: Optional[str] = None,
    name: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    normalized_id_card = normalize_id_card(id_card) if id_card else None
    """检查指定人员是否在黑名单中"""
    record = blacklist_crud.check_in_blacklist(
        db, student_id=student_id, id_card=normalized_id_card, name=name
    )
    
    if record:
        return {
            "code": 200,
            "data": {
                "in_blacklist": True,
                "record": {
                    "id": record.id,
                    "name": record.name,
                    "student_id": record.student_id,
                    "id_card": record.id_card,
                    "reason": record.reason,
                    "description": record.description,
                    "effective_from": record.effective_from,
                    "effective_to": record.effective_to
                }
            }
        }
    else:
        return {
            "code": 200,
            "data": {"in_blacklist": False}
        }