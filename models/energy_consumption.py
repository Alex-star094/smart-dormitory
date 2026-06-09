from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime
from utils.db import Base

class EnergyType(str, enum.Enum):
    """能源类型枚举"""
    ELECTRICITY = "electricity"  # 电力
    WATER = "water"              # 水
    GAS = "gas"                  # 燃气

class EnergyConsumption(Base):
    """能耗记录表模型"""
    __tablename__ = "energy_consumption"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dormitory = Column(String(20), nullable=False, index=True, comment="宿舍号")
    energy_type = Column(String(20), nullable=False, comment="能源类型")
    consumption = Column(Float, nullable=False, comment="消耗量")
    unit = Column(String(10), nullable=False, comment="单位（度/吨/立方米）")
    cost = Column(Float, nullable=False, comment="费用（元）")
    month = Column(String(7), nullable=False, comment="月份（YYYY-MM）")
    alarm = Column(Boolean, default=False, comment="是否告警（超过阈值）")
    alarm_reason = Column(String(100), nullable=True, comment="告警原因")
    created_at = Column(DateTime, default=datetime.now, comment="记录时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<EnergyConsumption(dormitory={self.dormitory}, type={self.energy_type}, month={self.month})>"
