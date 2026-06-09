from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text,Index,CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime
from utils.db import Base
from models.user import User

class BlacklistType(str, enum.Enum):
    """黑名单类型枚举"""
    STUDENT = "student"      # 学生
    VISITOR = "visitor"      # 访客
    EXTERNAL = "external"    # 外部人员
    SYSTEM = "system"        # 系统自动添加

class BlacklistReason(str, enum.Enum):
    """黑名单原因枚举"""
    DISCIPLINE = "discipline"        # 违纪行为
    SECURITY_RISK = "security_risk"  # 安全风险
    MULTIPLE_FAILURE = "multiple_failure"  # 多次验证失败
    ADMIN_MANUAL = "admin_manual"    # 管理员手动添加
    OTHER = "other"                  # 其他

class BlacklistStatus(str, enum.Enum):
    """黑名单状态"""
    ACTIVE = "active"      # 生效中
    EXPIRED = "expired"    # 已过期
    REMOVED = "removed"    # 已移除

class BlacklistRecord(Base):
    """黑名单记录表模型（优化id_card约束与索引）"""
    __tablename__ = "blacklist_records"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 身份信息：关键修改1→添加CheckConstraint，确保student_id和id_card至少一个非空
    student_id = Column(String(20), nullable=True, index=True, comment="学号")
    id_card = Column(String(18), nullable=True, index=True, comment="访客身份证号（已规范化为18位）")
    name = Column(String(50), nullable=False, comment="姓名")
    
    # 黑名单信息（不变）
    blacklist_type = Column(String(20), nullable=False, comment="类型")
    reason = Column(String(50), nullable=False, comment="原因")
    status = Column(String(20), default="active", comment="状态")
    description = Column(Text, nullable=True, comment="详细描述")
    
    # 时间信息（不变）
    effective_from = Column(DateTime, nullable=False, default=datetime.now, comment="生效时间")
    effective_to = Column(DateTime, nullable=True, comment="失效时间（空表示永久）")
    
    # 操作信息（不变）
    created_by = Column(Integer, nullable=False, comment="创建人ID（管理员）")
    removed_by = Column(Integer, nullable=True, comment="移除人ID")
    removal_reason = Column(String(200), nullable=True, comment="移除原因")
    
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关键修改2：添加索引与约束
    __table_args__ = (
        # 复合索引：优化按姓名+身份证号的联合查询（如黑名单检查）
        Index("idx_blacklist_name_idcard", "name", "id_card"),
        # 约束：student_id和id_card不能同时为空（至少填一个身份标识）
        CheckConstraint("student_id IS NOT NULL OR id_card IS NOT NULL", name="ck_blacklist_id_not_null"),
    )

    def __repr__(self):
        return f"<BlacklistRecord(name={self.name}, id_card={self.id_card}, status={self.status})>"
    
    def is_active(self) -> bool:
        """检查是否生效（逻辑不变）"""
        if self.status != BlacklistStatus.ACTIVE:
            return False
        now = datetime.now()
        if self.effective_to and now > self.effective_to:
            return False
        return now >= self.effective_from