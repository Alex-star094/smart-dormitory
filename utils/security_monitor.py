from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.access import AccessRecord, AccessStatus
from models.blacklist import BlacklistType, BlacklistReason
from config import settings

class SecurityMonitor:
    """安全监控类，自动检测异常行为"""
    
    @staticmethod
    def check_multiple_failures(db: Session, user_id: int, hours: int = 24):
        """检查指定时间内的多次验证失败"""
        time_threshold = datetime.now() - timedelta(hours=hours)
        
        failures = db.query(AccessRecord).filter(
            AccessRecord.user_id == user_id,
            AccessRecord.status == AccessStatus.DENIED,
            AccessRecord.access_time >= time_threshold
        ).count()
        
        # 如果24小时内失败超过5次，自动加入黑名单
        if failures >= 5:
            from crud.blacklist import blacklist_crud
            from crud.user import user_crud
            
            user = user_crud.get(db, id=user_id)
            if user:
                # 检查是否已在黑名单
                existing = blacklist_crud.check_in_blacklist(db, student_id=user.student_id)
                if not existing:
                    # 自动添加黑名单，24小时后自动解除
                    blacklist_crud.create(db, obj_in={
                        "student_id": user.student_id,
                        "name": user.username,
                        "blacklist_type": BlacklistType.STUDENT,
                        "reason": BlacklistReason.MULTIPLE_FAILURE,
                        "description": f"24小时内验证失败{failures}次",
                        "effective_to": datetime.now() + timedelta(hours=24),
                        "created_by": 0  # 系统自动
                    })
                    return True
        return False
    
    @staticmethod
    def check_suspicious_access(db: Session, dormitory: str, minutes: int = 5):
        """检查可疑的频繁通行"""
        time_threshold = datetime.now() - timedelta(minutes=minutes)
        
        # 统计同一宿舍在短时间内的大量通行
        access_count = db.query(AccessRecord).filter(
            AccessRecord.dormitory == dormitory,
            AccessRecord.access_time >= time_threshold
        ).count()
        
        # 如果5分钟内超过20次通行，触发告警
        if access_count >= 20:
            # 这里可以发送通知给管理员
            return True
        return False