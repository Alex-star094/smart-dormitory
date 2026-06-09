from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File,Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json
import base64
from crud.repair_record import repair_crud
from crud.user import user_crud
from api.auth import get_current_user, require_admin
from utils.db import get_db
from models.repair_record import RepairRecord
from models.user import User
# 移除未定义的RepairCreate相关引用，直接使用模型构建数据

router = APIRouter(prefix="", tags=["维修管理"])
# -------------------------- 基础常量定义 --------------------------
VALID_STATUSES = ["pending", "processing", "completed", "cancelled"]
VALID_PRIORITIES = ["低", "中", "高", "紧急"]
# -------------------------- 创建维修申请（核心修复：移除RepairCreate依赖） --------------------------
@router.post("", summary="学生提交报修申请", response_model=dict)
def create_repair_request(
    # 明确用Form接收所有参数，与前端表单格式匹配
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    priority: str = Form("中"),
    location: str = Form(...),
    contact_phone: str = Form(...),
    user_id: Optional[int] = Form(None),  # 接收前端传递的用户ID
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """学生创建维修记录（仅学生可调用）"""
    # 1. 权限校验：仅学生可提交
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅学生可提交报修申请"
        )
    # 2. 参数校验：必填项非空
    if not title.strip() or not description.strip() or not category.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="标题、描述、类别不能为空"
        )
    if not location.strip() or not contact_phone.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="位置和联系电话不能为空"
        )
    # 3. 确定用户ID（优先用前端传递的，否则用当前登录用户ID）
    final_user_id = user_id or current_user.id
    if not final_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户ID不存在"
        )
    # 4. 直接用RepairRecord模型构建数据（替换RepairCreate）
    try:
        repair = RepairRecord(
            dormitory=current_user.dormitory,  # 从当前用户获取宿舍号（已在个人中心绑定）
            user_id=final_user_id,
            title=title.strip(),
            description=description.strip(),
            category=category.strip(),
            priority=priority,  # 直接使用中文优先级（与VALID_PRIORITIES匹配）
            status="pending",  # 默认初始状态为待处理
            location=location.strip(),
            contact_phone=contact_phone.strip(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        # 写入数据库
        db.add(repair)
        db.commit()
        db.refresh(repair)  # 刷新实例获取自动生成的ID
    except Exception as e:
        db.rollback()  # 出错时回滚事务
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建报修记录失败：{str(e)}"
        )
    # 6. 返回成功结果，与前端判断逻辑匹配
    return {
        "code": 200,
        "msg": "报修申请提交成功",
        "data": {
            "repair_id": repair.id,
            "status": repair.status
        }
    }
# -------------------------- 获取我的维修申请（无修改） --------------------------
@router.get("/my", summary="获取我的维修申请")
def get_my_repairs(
    repair_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """学生查询自己的维修申请"""
    status_filter = None
    if repair_status:
        status_filter = repair_status.lower()
        if status_filter not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态！可选值：{VALID_STATUSES}"
            )
    
    repairs = repair_crud.get_by_user_id(
        db, user_id=current_user.id, status=status_filter, skip=skip, limit=limit
    )
    
    return {
        "code": 200,
        "data": {
            "total": len(repairs),
            "repairs": [
                {
                    "id": r.id,
                    "title": r.title,
                    "category": r.category,
                    "priority": r.priority,
                    "status": r.status,
                    "description": r.description,
                    "location": r.location,
                    "contact_phone": r.contact_phone,
                    "assigned_to": r.assigned_to,
                    "repair_notes": r.repair_notes,
                    "repair_result": r.repair_result,
                    "cost": r.cost,
                    "expected_time": r.expected_time,
                    "repair_time": r.repair_time,
                    "completed_time": r.completed_time,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at
                } for r in repairs
            ]
        }
    }
# -------------------------- 获取宿舍维修记录（无修改） --------------------------
@router.get("/dormitory", summary="获取宿舍维修记录")
def get_dormitory_repairs(
    dormitory: Optional[str] = None,
    repair_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询指定宿舍的维修记录（学生只能查自己宿舍，管理员可查所有）"""
    if current_user.role != "admin":
        dormitory = dormitory or current_user.dormitory
        if not dormitory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请先设置宿舍号，或指定要查询的宿舍号"
            )
    if not dormitory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="管理员需指定要查询的宿舍号"
        )
    
    status_filter = None
    if repair_status:
        status_filter = repair_status.lower()
        if status_filter not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态！可选值：{VALID_STATUSES}"
            )
    
    repairs = repair_crud.get_by_dormitory(
        db, dormitory=dormitory, status=status_filter, skip=skip, limit=limit
    )
    
    return {
        "code": 200,
        "data": {
            "total": len(repairs),
            "repairs": [
                {
                    "id": r.id,
                    "title": r.title,
                    "category": r.category,
                    "priority": r.priority,
                    "status": r.status,
                    "description": r.description,
                    "location": r.location,
                    "contact_phone": r.contact_phone,
                    "assigned_to": r.assigned_to,
                    "repair_notes": r.repair_notes,
                    "repair_result": r.repair_result,
                    "cost": r.cost,
                    "expected_time": r.expected_time,
                    "repair_time": r.repair_time,
                    "completed_time": r.completed_time,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at
                } for r in repairs
            ]
        }
    }
# -------------------------- 管理员获取所有维修记录（无修改） --------------------------
@router.get("/list", summary="管理员获取所有维修记录")
def get_repair_list(
    repair_status: Optional[str] = None,
    repair_priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理员查询所有维修记录（支持状态/优先级筛选）"""
    status_filter = None
    if repair_status:
        status_filter = repair_status.lower()
        if status_filter not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态！可选值：{VALID_STATUSES}"
            )
    
    priority_filter = None
    if repair_priority:
        if repair_priority not in VALID_PRIORITIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的优先级！可选值：{VALID_PRIORITIES}"
            )
        priority_filter = repair_priority
    
    query = db.query(RepairRecord)
    if status_filter:
        query = query.filter(RepairRecord.status == status_filter)
    if priority_filter:
        query = query.filter(RepairRecord.priority == priority_filter)
    
    total = query.count()
    repairs = query.order_by(RepairRecord.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "code": 200,
        "data": {
            "total": total,
            "repairs": [
                {
                    "id": r.id,
                    "dormitory": r.dormitory,
                    "user_id": r.user_id,
                    "title": r.title,
                    "category": r.category,
                    "priority": r.priority,
                    "status": r.status,
                    "description": r.description,
                    "location": r.location,
                    "contact_phone": r.contact_phone,
                    "assigned_to": r.assigned_to,
                    "repair_notes": r.repair_notes,
                    "repair_result": r.repair_result,
                    "cost": r.cost,
                    "expected_time": r.expected_time,
                    "repair_time": r.repair_time,
                    "completed_time": r.completed_time,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at
                } for r in repairs
            ]
        }
    }
# -------------------------- 指派维修人员（无修改） --------------------------
@router.put("/{repair_id}/assign", summary="指派维修人员")
def assign_repairer(
    repair_id: int,
    repairer_id: int = Form(...),  # 用Form接收表单参数，而非Body
    expected_time: Optional[str] = Form(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理员为维修记录指派维修人员"""
    repairer = user_crud.get(db, id=repairer_id)
    if not repairer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="维修人员不存在"
        )
    
    expected_time_dt = None
    if expected_time:
        try:
            expected_time_dt = datetime.strptime(expected_time, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="预计维修时间格式错误！正确格式：YYYY-MM-DD"
            )
    
    repair = repair_crud.assign_repairer(
        db, repair_id=repair_id, repairer_id=repairer_id, expected_time=expected_time
    )
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="维修记录不存在"
        )
    
    return {
        "code": 200,
        "msg": f"已指派维修人员（ID：{repairer_id}），维修状态更新为processing",
        "data": {
            "repair_id": repair.id,
            "assigned_to": repair.assigned_to,
            "status": repair.status,
            "expected_time": repair.expected_time
        }
    }
# -------------------------- 更新维修状态（无修改） --------------------------
@router.put("/{repair_id}/status", summary="更新维修状态")
def update_repair_status(
    repair_id: int,
    repair_status: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理员更新维修记录状态"""
    status_lower = repair_status.lower()
    if status_lower not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的状态！可选值：{VALID_STATUSES}"
        )
    
    repair = repair_crud.update_status(db, repair_id=repair_id, status=status_lower)
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="维修记录不存在"
        )
    
    return {
        "code": 200,
        "msg": f"维修状态已成功更新为：{repair.status}",
        "data": {
            "repair_id": repair.id,
            "status": repair.status,
            "updated_at": repair.updated_at
        }
    }
# -------------------------- 更新维修结果（无修改） --------------------------
@router.put("/{repair_id}/result", summary="更新维修结果")
def update_repair_result(
    repair_id: int,
    repair_notes: Optional[str] = Form(None),
    repair_result: Optional[str] = Form(None),
    cost: Optional[float] = Form(None),
    completed: bool = Form(False),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理员更新维修结果（支持标记完成）"""
    if cost is not None and cost < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="维修费用不能为负数"
        )
    
    repair = repair_crud.update_repair_result(
        db, repair_id=repair_id, repair_notes=repair_notes,
        repair_result=repair_result, cost=cost, completed=completed
    )
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="维修记录不存在"
        )
    
    msg = "维修结果已更新"
    if completed:
        repair.status = "completed"
        repair.completed_time = datetime.now()
    
    db.commit()
    db.refresh(repair)
    
    return {
        "code": 200,
        "msg": msg,
        "data": {
            "repair_id": repair.id,
            "repair_notes": repair.repair_notes,
            "repair_result": repair.repair_result,
            "cost": repair.cost,
            "status": repair.status,
            "completed_time": repair.completed_time
        }
    }
# -------------------------- 删除维修记录（无修改） --------------------------
@router.delete("/{repair_id}", summary="删除维修记录")
def delete_repair_record(
    repair_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理员删除维修记录"""
    repair = repair_crud.get(db, id=repair_id)
    if not repair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="维修记录不存在"
        )
    
    repair_crud.remove(db, id=repair_id)
    
    return {
        "code": 200,
        "msg": f"维修记录（ID：{repair_id}）已成功删除"
    }
# -------------------------- 绑定宿舍（无修改） --------------------------
@router.post("/bind-dorm", summary="绑定宿舍")
def bind_dormitory(
    dormitory: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """学生绑定宿舍号"""
    if not dormitory.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="宿舍号不能为空"
        )
    user = user_crud.update(
        db, 
        db_obj=current_user, 
        obj_in={"dormitory": dormitory.strip()}
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="绑定宿舍失败"
        )
    db.commit()
    db.refresh(user)
    return {
        "code": 200,
        "msg": "宿舍绑定成功",
        "data": {"dormitory": user.dormitory}
    }