from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from crud.energy_consumption import energy_crud
from api.auth import get_current_user, require_admin
from utils.db import get_db
from models.energy_consumption import EnergyConsumption, EnergyType
from models.user import User
from config import settings
from fastapi import Query

router = APIRouter()


# -------------------------- 辅助函数 --------------------------
def check_alarm(energy_type: str, consumption: float) -> tuple:
    """检查是否触发告警"""
    alarm = False
    alarm_reason = None
    
    if energy_type == EnergyType.ELECTRICITY.value:
        threshold = getattr(settings, "ELECTRICITY_ALARM_THRESHOLD", 300)
        if consumption > threshold:
            alarm = True
            alarm_reason = f"电力消耗超过阈值 {threshold}度"
    elif energy_type == EnergyType.WATER.value:
        threshold = getattr(settings, "WATER_ALARM_THRESHOLD", 20)
        if consumption > threshold:
            alarm = True
            alarm_reason = f"用水量超过阈值 {threshold}吨"
    
    return alarm, alarm_reason


def calculate_cost(energy_type: str, consumption: float) -> float:
    """计算费用"""
    if energy_type == EnergyType.ELECTRICITY.value:
        unit_price = getattr(settings, "ELECTRICITY_PRICE", 0.667)
        cost = round(consumption * unit_price, 2)
    elif energy_type == EnergyType.WATER.value:
        unit_price = getattr(settings, "WATER_PRICE", 4.05)
        cost = round(consumption * unit_price, 2)
    else:
        cost = 0.0
    return cost


# -------------------------- 能耗列表接口（新增） --------------------------
@router.get("/list", summary="获取能耗列表")
def get_energy_list(
    dormitory: Optional[str] = None,
    energy_type: Optional[str] = None,
    month: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取能耗列表
    - 学生：只能查看自己宿舍的能耗
    - 管理员：可以查看所有宿舍能耗，支持宿舍搜索
    """
    # 学生只能查自己宿舍
    if current_user.role != "admin":
        dormitory = current_user.dormitory
        if not dormitory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请先设置宿舍号"
            )
    
    # 验证能源类型
    energy_type_enum = None
    if energy_type:
        try:
            energy_type_enum = EnergyType(energy_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的能源类型，可选值：{[e.value for e in EnergyType]}"
            )
    
    # 构建查询
    query = db.query(EnergyConsumption)
    
    # 添加过滤条件
    if dormitory:
        query = query.filter(EnergyConsumption.dormitory == dormitory)
    
    if energy_type_enum:
        query = query.filter(EnergyConsumption.energy_type == energy_type_enum.value)
    
    if month:
        query = query.filter(EnergyConsumption.month == month)
    
    # 获取总数
    total = query.count()
    
    # 获取分页数据
    records = query.order_by(
        EnergyConsumption.month.desc(),
        EnergyConsumption.dormitory
    ).offset(skip).limit(limit).all()
    
    # 处理返回数据，添加费用计算和告警检查
    processed_records = []
    for record in records:
        # 计算费用
        cost = calculate_cost(record.energy_type, record.consumption)
        
        # 检查是否触发告警（如果数据库中没有告警状态，则动态检查）
        if not record.alarm:
            alarm, alarm_reason = check_alarm(record.energy_type, record.consumption)
        else:
            alarm = record.alarm
            alarm_reason = record.alarm_reason
        
        processed_records.append({
            "id": record.id,
            "dormitory": record.dormitory,
            "energy_type": record.energy_type,
            "energy_type_cn": "电力" if record.energy_type == EnergyType.ELECTRICITY.value else "用水",
            "consumption": record.consumption,
            "unit": record.unit,
            "cost": cost,
            "month": record.month,
            "alarm": alarm,
            "alarm_reason": alarm_reason,
            "created_at": record.created_at
        })
    
    return {
        "code": 200,
        "data": {
            "total": total,
            "records": processed_records,
            "page": {
                "skip": skip,
                "limit": limit,
                "has_more": total > (skip + limit)
            }
        }
    }


@router.get("/records", summary="查询能耗记录")
def get_energy_records(
    dormitory: Optional[str] = None,
    energy_type: Optional[str] = None,
    month: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询能耗记录（学生只能查自己宿舍，管理员可查所有）"""
    # 学生默认查自己宿舍
    if current_user.role != "admin":
        dormitory = dormitory or current_user.dormitory
        if not dormitory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请先设置宿舍号"
            )
    
    # 验证能源类型
    energy_type_enum = None
    if energy_type:
        try:
            energy_type_enum = EnergyType(energy_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的能源类型，可选值：{[e.value for e in EnergyType]}"
            )
    
    # 查询记录（新增：调用CRUD时触发费用自动计算）
    if dormitory:
        records = energy_crud.get_by_dormitory(
            db, dormitory=dormitory, energy_type=energy_type_enum, 
            month=month, skip=skip, limit=limit
        )
    elif month:
        records = energy_crud.get_by_month(db, month=month, skip=skip, limit=limit)
    else:
        records = energy_crud.get_multi(db, skip=skip, limit=limit)
    
    # 补充：自动计算费用（若CRUD层未实现，此处兜底计算）
    for record in records:
        try:
            # 按能源类型自动计算费用（水电单价从配置/常量获取，兼容原逻辑）
            if record.energy_type == EnergyType.ELECTRICITY.value:
                unit_price = getattr(settings, "ELECTRICITY_PRICE", 0.667)  # 电费默认0.667元/度
                record.cost = round(record.consumption * unit_price, 2)
            elif record.energy_type == EnergyType.WATER.value:
                unit_price = getattr(settings, "WATER_PRICE", 4.05)  # 水费默认4.05元/吨
                record.cost = round(record.consumption * unit_price, 2)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"费用计算失败：{str(e)}"
            )
    
    return {
        "code": 200,
        "data": {
            "total": len(records),
            "records": [
                {
                    "id": r.id,
                    "dormitory": r.dormitory,
                    "energy_type": r.energy_type,
                    "consumption": r.consumption,
                    "unit": r.unit,
                    "cost": r.cost,  # 自动计算后的费用
                    "month": r.month,
                    "alarm": r.alarm,
                    "alarm_reason": r.alarm_reason,
                    "created_at": r.created_at
                } for r in records
            ]
        }
    }

@router.get("/alarms", summary="查询能耗告警")
def get_energy_alarms(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理员查询能耗告警记录"""
    records = energy_crud.get_alarm_records(db, skip=skip, limit=limit)
    
    return {
        "code": 200,
        "data": {
            "total": len(records),
            "alarms": [
                {
                    "id": r.id,
                    "dormitory": r.dormitory,
                    "energy_type": r.energy_type,
                    "consumption": r.consumption,
                    "unit": r.unit,
                    "cost": r.cost,
                    "month": r.month,
                    "alarm_reason": r.alarm_reason,
                    "created_at": r.created_at
                } for r in records
            ]
        }
    }

@router.get("/statistics", summary="能耗统计")
def get_energy_statistics(
    dormitory: str,
    start_month: str,
    end_month: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取宿舍能耗统计"""
    # 学生只能查自己宿舍
    if current_user.role != "admin" and current_user.dormitory != dormitory:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能查询自己宿舍的能耗统计"
        )
    
    statistics = energy_crud.get_statistics(db, dormitory, start_month, end_month)
    
    # 补充：统计结果中的费用自动计算（若CRUD层返回的是原始数据）
    processed_statistics = []
    for stat in statistics:
        energy_type, total_consumption, _ = stat
        try:
            if energy_type == EnergyType.ELECTRICITY.value:
                unit_price = getattr(settings, "ELECTRICITY_PRICE", 0.667)
                total_cost = round(total_consumption * unit_price, 2)
            elif energy_type == EnergyType.WATER.value:
                unit_price = getattr(settings, "WATER_PRICE", 4.05)
                total_cost = round(total_consumption * unit_price, 2)
            else:
                total_cost = 0.0
            processed_statistics.append((energy_type, total_consumption, total_cost))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"统计费用计算失败：{str(e)}"
            )
    
    return {
        "code": 200,
        "data": {
            "dormitory": dormitory,
            "period": f"{start_month} 至 {end_month}",
            "statistics": [
                {
                    "energy_type": stat[0],
                    "total_consumption": stat[1],
                    "total_cost": stat[2]  # 自动计算后的总费用
                } for stat in processed_statistics
            ]
        }
    }

# -------------------------- 核心修改：替换原“添加记录”为“查询+告警” --------------------------
@router.get("/admin/records", summary="管理员查询所有宿舍能耗记录")
def admin_get_all_records(
    dormitory: Optional[str] = None,
    energy_type: Optional[str] = None,
    month: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_admin),  # 仅管理员可访问
    db: Session = Depends(get_db)
):
    """管理员查询所有宿舍能耗记录（支持筛选，含费用自动计算）"""
    # 验证能源类型
    energy_type_enum = None
    if energy_type:
        try:
            energy_type_enum = EnergyType(energy_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的能源类型，可选值：{[e.value for e in EnergyType]}"
            )
    
    # 管理员查询逻辑（支持按宿舍、能源类型、月份筛选）
    query = db.query(EnergyConsumption)
    if dormitory:
        query = query.filter(EnergyConsumption.dormitory == dormitory)
    if energy_type_enum:
        query = query.filter(EnergyConsumption.energy_type == energy_type_enum.value)
    if month:
        query = query.filter(EnergyConsumption.month == month)
    
    records = query.order_by(EnergyConsumption.month.desc()).offset(skip).limit(limit).all()
    
    # 自动计算费用
    for record in records:
        try:
            if record.energy_type == EnergyType.ELECTRICITY.value:
                unit_price = getattr(settings, "ELECTRICITY_PRICE", 0.667)
                record.cost = round(record.consumption * unit_price, 2)
            elif record.energy_type == EnergyType.WATER.value:
                unit_price = getattr(settings, "WATER_PRICE", 4.05)
                record.cost = round(record.consumption * unit_price, 2)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"费用计算失败：{str(e)}"
            )
    
    return {
        "code": 200,
        "data": {
            "total": len(records),
            "filter_conditions": {
                "dormitory": dormitory,
                "energy_type": energy_type_enum.value if energy_type_enum else None,
                "month": month
            },
            "records": [
                {
                    "id": r.id,
                    "dormitory": r.dormitory,
                    "energy_type": r.energy_type,
                    "consumption": r.consumption,
                    "unit": r.unit,
                    "cost": r.cost,
                    "month": r.month,
                    "alarm": r.alarm,
                    "alarm_reason": r.alarm_reason,
                    "created_at": r.created_at
                } for r in records
            ]
        }
    }

# -------------------------- 管理员搜索接口（新增） --------------------------
@router.get("/admin/search", summary="管理员搜索能耗记录")
def admin_search_energy(
    keyword: Optional[str] = None,
    dormitory: Optional[str] = None,
    energy_type: Optional[str] = None,
    month: Optional[str] = None,
    has_alarm: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理员搜索能耗记录（支持关键词、宿舍、能源类型、月份、告警状态）"""
    # 构建查询
    query = db.query(EnergyConsumption)
    
    # 添加过滤条件
    if dormitory:
        query = query.filter(EnergyConsumption.dormitory == dormitory)
    
    if energy_type:
        try:
            energy_type_enum = EnergyType(energy_type)
            query = query.filter(EnergyConsumption.energy_type == energy_type_enum.value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的能源类型，可选值：{[e.value for e in EnergyType]}"
            )
    
    if month:
        query = query.filter(EnergyConsumption.month == month)
    
    if has_alarm is not None:
        query = query.filter(EnergyConsumption.alarm == has_alarm)
    
    # 关键词搜索（支持宿舍模糊搜索）
    if keyword:
        query = query.filter(EnergyConsumption.dormitory.contains(keyword))
    
    # 获取总数
    total = query.count()
    
    # 获取分页数据
    records = query.order_by(
        EnergyConsumption.month.desc(),
        EnergyConsumption.dormitory
    ).offset(skip).limit(limit).all()
    
    # 处理返回数据
    processed_records = []
    for record in records:
        # 计算费用
        cost = calculate_cost(record.energy_type, record.consumption)
        
        processed_records.append({
            "id": record.id,
            "dormitory": record.dormitory,
            "energy_type": record.energy_type,
            "energy_type_cn": "电力" if record.energy_type == EnergyType.ELECTRICITY.value else "用水",
            "consumption": record.consumption,
            "unit": record.unit,
            "cost": cost,
            "month": record.month,
            "alarm": record.alarm,
            "alarm_reason": record.alarm_reason,
            "created_at": record.created_at
        })
    
    return {
        "code": 200,
        "data": {
            "total": total,
            "records": processed_records,
            "page": {
                "skip": skip,
                "limit": limit,
                "has_more": total > (skip + limit)
            }
        }
    }


@router.post("/admin/record/{record_id}/alarm", summary="管理员手动触发能耗告警")
def admin_trigger_alarm(
    record_id: int,
    alarm_reason: Optional[str] = None,
    current_user: User = Depends(require_admin),  # 仅管理员可操作
    db: Session = Depends(get_db)
):
    """管理员查询到异常能耗记录后，手动触发告警"""
    # 1. 查找目标记录
    record = db.query(EnergyConsumption).filter(EnergyConsumption.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"能耗记录不存在（ID：{record_id}）"
        )
    
    # 2. 自动生成默认告警原因（若未传入）
    if not alarm_reason:
        threshold_key = f"{record.energy_type.upper()}_ALARM_THRESHOLD"
        default_threshold = getattr(settings, threshold_key, 0)
        alarm_reason = f"{record.energy_type}消耗异常（当前{record.consumption}{record.unit}，参考阈值{default_threshold}{record.unit}）"
    
    # 3. 更新告警状态
    record.alarm = True
    record.alarm_reason = alarm_reason
    db.commit()
    db.refresh(record)
    
    return {
        "code": 200,
        "msg": "告警触发成功",
        "data": {
            "id": record.id,
            "dormitory": record.dormitory,
            "energy_type": record.energy_type,
            "alarm": record.alarm,
            "alarm_reason": record.alarm_reason
        }
    }

@router.get("/current-month", summary="查询当月能耗")
def get_current_month_energy(
    dormitory: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询当月能耗（学生查自己宿舍，管理员可查所有或指定宿舍）"""
    # 获取当前月份
    current_month = datetime.now().strftime("%Y-%m")
    
    # 学生默认查自己宿舍
    if current_user.role != "admin":
        dormitory = dormitory or current_user.dormitory
        if not dormitory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请先设置宿舍号"
            )
    
    query = db.query(EnergyConsumption).filter(
        EnergyConsumption.month == current_month
    )
    
    if dormitory:
        query = query.filter(EnergyConsumption.dormitory == dormitory)
    
    records = query.all()
    
    # 分类统计（补充：自动计算当月费用）
    electricity = next((r for r in records if r.energy_type == EnergyType.ELECTRICITY.value), None)
    water = next((r for r in records if r.energy_type == EnergyType.WATER.value), None)
    
    # 计算电费
    if electricity:
        elec_price = getattr(settings, "ELECTRICITY_PRICE", 0.667)
        electricity.cost = round(electricity.consumption * elec_price, 2)
    # 计算水费
    if water:
        water_price = getattr(settings, "WATER_PRICE", 4.05)
        water.cost = round(water.consumption * water_price, 2)
    
    return {
        "code": 200,
        "data": {
            "month": current_month,
            "dormitory": dormitory,
            "electricity": {
                "consumption": electricity.consumption if electricity else 0,
                "unit": electricity.unit if electricity else "度",
                "cost": electricity.cost if electricity else 0,  # 自动计算后费用
                "alarm": electricity.alarm if electricity else False
            },
            "water": {
                "consumption": water.consumption if water else 0,
                "unit": water.unit if water else "吨",
                "cost": water.cost if water else 0,  # 自动计算后费用
                "alarm": water.alarm if water else False
            }
        }
    }

@router.post("/record", summary="学生添加能耗记录")
def student_add_energy_record(
    dormitory: str,
    energy_type: str,
    consumption: float,
    unit: str,
    month: str,
    current_user: User = Depends(get_current_user),  # 学生/管理员均可调用，但校验宿舍号
    db: Session = Depends(get_db)
):
    """
    学生添加能耗记录（仅能添加自己宿舍的记录，费用自动计算）
    - 学生：仅能提交自己宿舍的记录，宿舍号与用户信息绑定
    - 管理员：可提交任意宿舍的记录（可选扩展）
    """

    # 1. 权限校验：学生只能添加自己宿舍的记录
    if current_user.role != "admin" and current_user.dormitory != dormitory:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能添加自己宿舍的能耗记录"
        )
    
    # 2. 基础参数校验
    # 验证能源类型
    try:
        energy_type_enum = EnergyType(energy_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的能源类型，可选值：{[e.value for e in EnergyType]}"
        )
    # 验证月份格式（YYYY-MM）
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="月份格式错误，需为 'YYYY-MM'（如 2025-03）"
        )
    # 验证消耗量非负
    if consumption < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消耗量不能为负数"
        )
    # 验证单位与能源类型匹配
    valid_unit_map = {
        "electricity": ["度", "kWh"],
        "water": ["吨", "m³"]
    }
    if unit not in valid_unit_map[energy_type]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{energy_type} 类型的有效单位为：{valid_unit_map[energy_type]}"
        )
    
    # 3. 自动计算费用（复用CRUD层的calculate_cost方法）
    try:
        cost = energy_crud.calculate_cost(
            energy_type=energy_type_enum.value,
            consumption=consumption,
            unit=unit
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # 4. 检查是否触发告警（可选，按阈值判断）
    alarm = False
    alarm_reason = None
    if energy_type_enum == EnergyType.ELECTRICITY and consumption > settings.ELECTRICITY_ALARM_THRESHOLD:
        alarm = True
        alarm_reason = f"电力消耗超过阈值 {settings.ELECTRICITY_ALARM_THRESHOLD}{unit}（当前：{consumption}{unit}）"
    elif energy_type_enum == EnergyType.WATER and consumption > settings.WATER_ALARM_THRESHOLD:
        alarm = True
        alarm_reason = f"用水量超过阈值 {settings.WATER_ALARM_THRESHOLD}{unit}（当前：{consumption}{unit}）"
    
    # 5. 数据库写入（关键步骤：add + commit）
    try:
        # 创建记录对象
        new_record = EnergyConsumption(
            dormitory=dormitory,
            energy_type=energy_type_enum.value,
            consumption=consumption,
            unit=unit,
            cost=cost,
            month=month,
            alarm=alarm,
            alarm_reason=alarm_reason,
            created_at=datetime.now()  # 若模型有默认值可省略
        )
        # 写入数据库
        db.add(new_record)
        db.commit()  # 提交事务（必须，否则数据仅在会话中，未写入数据库）
        db.refresh(new_record)  # 刷新对象，获取数据库生成的ID等信息
    except Exception as e:
        db.rollback()  # 异常时回滚，避免事务残留
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据写入失败：{str(e)}"
        )
    
    # 6. 返回成功响应
    return {
        "code": 200,
        "msg": "能耗记录添加成功",
        "data": {
            "id": new_record.id,  # 数据库生成的唯一ID（验证写入成功的标志）
            "dormitory": new_record.dormitory,
            "energy_type": new_record.energy_type,
            "consumption": new_record.consumption,
            "cost": new_record.cost,  # 自动计算的费用
            "alarm": new_record.alarm
        }
    }
