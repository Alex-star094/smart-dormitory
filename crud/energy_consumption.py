"""能耗记录CRUD模块"""
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from crud.base import BaseCRUD
from models.energy_consumption import EnergyConsumption, EnergyType

class EnergyConsumptionCRUD(BaseCRUD[EnergyConsumption, None, None]):
    """能耗记录CRUD类"""

    WATER_PRICE = 4.05  # 水费：4.05元/吨
    ELECTRICITY_PRICE = 0.667  # 电费：0.667元/度

    def __init__(self, model: EnergyConsumption):
        super().__init__(model)

    def create(self, db: Session, *, obj_in: dict) -> EnergyConsumption:
        """创建能耗记录，自动计算费用"""
        # 安全获取能源类型（兼容字符串和枚举）
        energy_type_raw = obj_in.get("energy_type")
        if hasattr(energy_type_raw, "value"):
            energy_type_str = energy_type_raw.value
        else:
            energy_type_str = str(energy_type_raw) if energy_type_raw else ""

        consumption = obj_in.get("consumption", 0)
        unit = obj_in.get("unit")

        # 根据能耗类型自动计算费用
        cost = self.calculate_cost(energy_type_str, consumption, unit)

        # 创建数据库对象
        db_obj = EnergyConsumption(
            dormitory=obj_in.get("dormitory"),
            energy_type=energy_type_str.lower(),
            consumption=consumption,
            unit=unit,
            cost=cost,
            month=obj_in.get("month"),
            alarm=obj_in.get("alarm", False),
            alarm_reason=obj_in.get("alarm_reason"),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def calculate_cost(self, energy_type: str, consumption: float, unit: str = None) -> float:
        """根据能耗类型和用量计算费用"""
        energy_type_lower = energy_type.lower()
        
        if energy_type_lower == "water" or unit == "吨":
            # 水费：用量(吨) × 4.05
            return round(consumption * self.WATER_PRICE, 2)
        elif energy_type_lower == "electricity" or unit == "度":
            # 电费：用量(度) × 0.667
            return round(consumption * self.ELECTRICITY_PRICE, 2)
        else:
            # 其他能耗类型，需要手动传入费用
            raise ValueError(f"无法自动计算 {energy_type} 的费用，请手动提供cost参数")

    def update(self, db: Session, *, db_obj: EnergyConsumption, obj_in: dict) -> EnergyConsumption:
        """更新能耗记录，重新计算费用"""
        # 如果consumption或energy_type被更新，重新计算费用
        if "consumption" in obj_in or "energy_type" in obj_in or "unit" in obj_in:
            energy_type = obj_in.get("energy_type", db_obj.energy_type)
            consumption = obj_in.get("consumption", db_obj.consumption)
            unit = obj_in.get("unit", db_obj.unit)
            
            # 重新计算费用
            try:
                cost = self.calculate_cost(energy_type, consumption, unit)
                obj_in["cost"] = cost
            except ValueError:
                # 如果不能自动计算，则使用传入的费用或保持原费用
                if "cost" not in obj_in:
                    obj_in["cost"] = db_obj.cost
        
        return super().update(db, db_obj=db_obj, obj_in=obj_in)

    def get_by_dormitory(
        self, db: Session, dormitory: str, 
        energy_type: Optional[EnergyType] = None,
        month: Optional[str] = None,
        skip: int = 0, limit: int = 100
    ) -> List[EnergyConsumption]:
        """根据宿舍号查询能耗记录"""
        query = db.query(EnergyConsumption).filter(EnergyConsumption.dormitory == dormitory)
        if energy_type:
            energy_type_str = energy_type.value
            query = query.filter(EnergyConsumption.energy_type == energy_type_str)
        if month:
            query = query.filter(EnergyConsumption.month == month)
        return query.order_by(EnergyConsumption.month.desc()).offset(skip).limit(limit).all()

    def get_by_month(
        self, db: Session, month: str, skip: int = 0, limit: int = 100
    ) -> List[EnergyConsumption]:
        """根据月份查询能耗记录"""
        return db.query(EnergyConsumption)\
            .filter(EnergyConsumption.month == month)\
            .order_by(EnergyConsumption.dormitory)\
            .offset(skip).limit(limit).all()

    def get_alarm_records(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[EnergyConsumption]:
        """查询告警记录"""
        return db.query(EnergyConsumption)\
            .filter(EnergyConsumption.alarm == True)\
            .order_by(EnergyConsumption.created_at.desc())\
            .offset(skip).limit(limit).all()

    def get_statistics(
        self, db: Session, dormitory: str, start_month: str, end_month: str
    ) -> List[Tuple[str, float, float]]:
        """获取宿舍能耗统计"""
        query = db.query(
            EnergyConsumption.energy_type,
            func.sum(EnergyConsumption.consumption),
            func.sum(EnergyConsumption.cost)
        ).filter(
            EnergyConsumption.dormitory == dormitory,
            EnergyConsumption.month >= start_month,
            EnergyConsumption.month <= end_month
        ).group_by(EnergyConsumption.energy_type)
        
        return query.all()

# 实例化能耗CRUD
energy_crud = EnergyConsumptionCRUD(EnergyConsumption)
