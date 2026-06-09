"""访客CRUD模块"""
from typing import List, Optional

from sqlalchemy.orm import Session

from crud.base import BaseCRUD
from models.visitor import Visitor, VisitorStatus
from utils.id_card_utils import normalize_id_card


class VisitorCRUD(BaseCRUD[Visitor, None, None]):
    """访客CRUD类"""
    def __init__(self, model: Visitor):
        super().__init__(model)

    def create(self, db: Session, *, obj_in: dict) -> Visitor:
        """创建访客预约记录"""
        id_card = obj_in.get("id_card", "")
        normalized_id_card = normalize_id_card(id_card)
        if not normalized_id_card:
            raise ValueError("身份证号格式无效，无法创建预约")

        status_enum = obj_in.get("status", VisitorStatus.PENDING)
        if hasattr(status_enum, "value"):
            status_str = status_enum.value
        else:
            status_str = str(status_enum).lower()

        db_obj = Visitor(
            user_id=obj_in.get("user_id"),
            visitor_name=obj_in.get("visitor_name"),
            id_card=normalized_id_card,
            visit_date=obj_in.get("visit_date"),
            visit_reason=obj_in.get("visit_reason"),
            status=status_str,
            approver_id=obj_in.get("approver_id"),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_user_id(
        self, db: Session, user_id: int, status: Optional[VisitorStatus] = None, skip: int = 0, limit: int = 100
    ) -> List[Visitor]:
        """根据预约人ID查询访客预约"""
        query = db.query(Visitor).filter(Visitor.user_id == user_id)
        if status:
            status_str = status.value.lower()
            query = query.filter(Visitor.status == status_str)
        return query.offset(skip).limit(limit).all()

    def update_approval(
        self, db: Session, *, visitor_id: int, status: VisitorStatus, approver_id: int, approve_note: Optional[str] = None
    ) -> Optional[Visitor]:
        """更新访客预约审核状态"""
        visitor = self.get(db, id=visitor_id)
        if not visitor:
            return None
        visitor.status = status.value.lower()
        visitor.approver_id = approver_id
        visitor.approve_note = approve_note
        db.commit()
        db.refresh(visitor)
        return visitor

# 实例化访客CRUD
visitor_crud = VisitorCRUD(Visitor)