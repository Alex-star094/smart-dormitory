"""黑名单CRUD模块"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from crud.base import BaseCRUD
from models.blacklist import BlacklistRecord, BlacklistStatus
from utils.id_card_utils import normalize_id_card

class BlacklistCRUD(BaseCRUD[BlacklistRecord, None, None]):
    """黑名单CRUD类"""
    def __init__(self, model: BlacklistRecord):
        super().__init__(model)

    def create(self, db: Session, *, obj_in: dict) -> BlacklistRecord:
        """创建黑名单记录"""
        id_card = obj_in.get("id_card")
        normalized_id_card = normalize_id_card(id_card) if id_card else None
        if id_card and not normalized_id_card:
            raise ValueError("身份证号格式无效，无法添加到黑名单")

        # 安全获取枚举值（兼容字符串和枚举对象）
        blacklist_type = obj_in.get("blacklist_type")
        if hasattr(blacklist_type, "value"):
            blacklist_type = blacklist_type.value
        blacklist_type = str(blacklist_type).lower() if blacklist_type else ""

        reason = obj_in.get("reason")
        if hasattr(reason, "value"):
            reason = reason.value
        reason = str(reason) if reason else ""

        status = obj_in.get("status", BlacklistStatus.ACTIVE)
        if hasattr(status, "value"):
            status = status.value
        status = str(status).lower() if status else "active"

        db_obj = BlacklistRecord(
            student_id=obj_in.get("student_id"),
            id_card=normalized_id_card,
            name=obj_in.get("name"),
            blacklist_type=blacklist_type,
            reason=reason,
            description=obj_in.get("description"),
            status=status,
            effective_from=obj_in.get("effective_from", datetime.now()),
            effective_to=obj_in.get("effective_to"),
            created_by=obj_in.get("created_by"),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def check_in_blacklist(
        self, db: Session, *, 
        student_id: Optional[str] = None,
        id_card: Optional[str] = None,
        name: Optional[str] = None
    ) -> Optional[BlacklistRecord]:
        """检查是否在黑名单中"""
        query = db.query(BlacklistRecord).filter(
            BlacklistRecord.status == BlacklistStatus.ACTIVE
        )
        
        conditions = []
        if student_id:
            conditions.append(BlacklistRecord.student_id == student_id)
        if id_card:
            normalized_id_card = normalize_id_card(id_card)
            conditions.append(BlacklistRecord.id_card == normalized_id_card)
        if name:
            conditions.append(BlacklistRecord.name == name)
        
        if not conditions:
            return None
        
        query = query.filter(or_(*conditions))
        
        # 检查时间有效性
        now = datetime.now()
        query = query.filter(
            BlacklistRecord.effective_from <= now,
            (BlacklistRecord.effective_to.is_(None)) | (BlacklistRecord.effective_to >= now)
        )
        
        return query.first()

    def get_active_records(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[BlacklistRecord]:
        """获取生效中的黑名单记录"""
        now = datetime.now()
        return db.query(BlacklistRecord).filter(
            BlacklistRecord.status == BlacklistStatus.ACTIVE,
            BlacklistRecord.effective_from <= now,
            (BlacklistRecord.effective_to.is_(None)) | (BlacklistRecord.effective_to >= now)
        ).offset(skip).limit(limit).all()

    def update_status(
        self, db: Session, *, record_id: int, 
        status: BlacklistStatus, removed_by: Optional[int] = None,
        removal_reason: Optional[str] = None
    ) -> Optional[BlacklistRecord]:
        """更新黑名单状态"""
        record = self.get(db, id=record_id)
        if not record:
            return None
        
        record.status = status.value.lower()
        if status == BlacklistStatus.REMOVED:
            record.removed_by = removed_by
            record.removal_reason = removal_reason
        
        db.commit()
        # db.refresh(record)
        return record

# 实例化黑名单CRUD
blacklist_crud = BlacklistCRUD(BlacklistRecord)