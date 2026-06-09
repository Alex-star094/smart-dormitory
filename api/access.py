from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import base64

from crud.access import access_crud
from crud.user import user_crud
from crud.blacklist import blacklist_crud  
from api.auth import get_current_user, require_admin
from utils.db import get_db
from utils.face_utils import (
    extract_face_embedding, 
    base64_to_embedding, 
    compare_faces, 
    preprocess_image_for_face_detection
)
from utils.auth_utils import create_access_token  # 引入公共Token工具
from config import settings
from models.access import AccessRecord
from models.user import User
from models.blacklist import BlacklistType  

router = APIRouter()
VALID_STATUSES = ["allowed", "denied", "error"]


@router.post("/face", summary="人脸识别通行（硬件调用）")
def face_access(
    student_id: str,
    dormitory: str,
    db: Session = Depends(get_db)
):
    """硬件专用：传入学号+宿舍，直接验证通行（假设硬件已完成人脸比对）"""
    try:
        # 1. 查询用户
        user = user_crud.get_by_student_id(db, student_id=student_id)
        if not user or not user.face_encoding:
            # 记录未授权通行
            access_crud.create(db, obj_in={
                "user_id": user.id if user else None,
                "username": user.username if user else "未知用户",
                "dormitory": dormitory,
                "status": "denied",
                "access_type": "face",
                "access_time": datetime.now(),
                "alarm": True,
                "notes": "未录入人脸信息" if user else "用户不存在"
            })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未授权用户或未录入人脸信息"
            )
        
        # 2. 校验宿舍绑定
        if not user.dormitory or user.dormitory.strip() == "":
            access_crud.create(db, obj_in={
                "user_id": user.id,
                "username": user.username,
                "dormitory": dormitory,
                "status": "denied",
                "access_type": "face",
                "access_time": datetime.now(),
                "alarm": True,
                "notes": "用户未绑定宿舍，无法验证通行权限"
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"学号{student_id}（{user.username}）未绑定宿舍，请先完善宿舍信息"
            )
        
        # 3. 校验宿舍匹配
        if user.dormitory != dormitory:
            access_crud.create(db, obj_in={
                "user_id": user.id,
                "username": user.username,
                "dormitory": dormitory,
                "status": "denied",
                "access_type": "face",
                "access_time": datetime.now(),
                "alarm": True,
                "notes": f"宿舍不匹配：用户绑定宿舍{user.dormitory}，提交宿舍{dormitory}"
            })
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"宿舍号错误！您绑定的宿舍是{user.dormitory}，请勿尝试非本人宿舍通行"
            )
        
        # 4. 黑名单校验
        blacklist_record = blacklist_crud.check_in_blacklist(
            db, student_id=user.student_id, name=user.username
        )
        if blacklist_record:
            access_crud.create(db, obj_in={
                "user_id": user.id,
                "username": user.username,
                "dormitory": dormitory,
                "status": "denied",
                "access_type": "face",
                "access_time": datetime.now(),
                "alarm": True,
                "notes": f"黑名单禁止通行 - 原因: {blacklist_record.reason}"
            })
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"您已被禁止通行，原因: {blacklist_record.reason}"
            )
        
        # 5. 记录通行并返回
        access_record = access_crud.create(db, obj_in={
            "user_id": user.id,
            "username": user.username,
            "dormitory": dormitory,
            "status": "allowed",
            "access_type": "face",
            "access_time": datetime.now(),
            "alarm": False
        })
        return {
            "code": 200,
            "msg": "人脸识别成功，允许通行",
            "data": {
                "username": user.username,
                "dormitory": dormitory,
                "access_time": access_record.access_time
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        access_crud.create(db, obj_in={
            "user_id": None,
            "username": "系统异常",
            "dormitory": dormitory,
            "status": "error",
            "access_type": "face",
            "access_time": datetime.now(),
            "alarm": True,
            "notes": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"人脸识别通行失败：{str(e)}"
        )


@router.post("/face/verify", summary="人脸验证（登录/通行双场景）")
async def face_verify_access(
    file: UploadFile = File(...),
    dormitory: Optional[str] = None,  # 可选：登录不传，通行传
    db: Session = Depends(get_db)
):
    """
    上传人脸图片验证：
    - 登录场景：不传dormitory → 返回Token
    - 通行场景：传dormitory → 验证宿舍后返回通行结果
    """
    try:
        # 1. 校验文件类型
        if not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请上传图片文件（jpg/png）"
            )
        
        # 2. 处理图片并提取人脸特征
        contents = await file.read()
        processed_contents = preprocess_image_for_face_detection(contents)
        face_embedding = extract_face_embedding(processed_contents)
        
        # 3. 比对所有已录入人脸的用户
        users_with_face = db.query(User).filter(User.face_encoding.isnot(None)).all()
        best_match = None
        best_similarity = 0.0
        threshold = settings.FACE_MATCH_THRESHOLD  # 配置中的人脸匹配阈值

        for user in users_with_face:
            try:
                # 解码用户存储的人脸特征
                stored_embedding = base64_to_embedding(user.face_encoding)
                # 比对相似度
                is_match, similarity = compare_faces(face_embedding, stored_embedding, threshold)
                if is_match and similarity > best_similarity:
                    best_match = user
                    best_similarity = similarity
            except Exception:
                # 跳过解码失败的用户（避免单个用户异常影响整体）
                continue
        
        # 4. 无匹配用户处理
        if not best_match:
            access_crud.create(db, obj_in={
                "user_id": None,
                "username": "未知用户",
                "dormitory": dormitory or "登录场景",
                "status": "denied",
                "access_type": "face",
                "access_time": datetime.now(),
                "alarm": True,
                "notes": f"人脸不匹配，最高相似度: {best_similarity:.3f}"
            })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="人脸识别失败，未找到匹配用户"
            )
        
        # 5. 黑名单校验（通用）
        blacklist_record = blacklist_crud.check_in_blacklist(
            db, student_id=best_match.student_id, name=best_match.username
        )
        if blacklist_record:
            access_crud.create(db, obj_in={
                "user_id": best_match.id,
                "username": best_match.username,
                "dormitory": dormitory or best_match.dormitory,
                "status": "denied",
                "access_type": "face",
                "access_time": datetime.now(),
                "alarm": True,
                "notes": f"黑名单禁止通行 - 原因: {blacklist_record.reason}, 相似度: {best_similarity:.3f}"
            })
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"您已被禁止操作，原因: {blacklist_record.reason}"
            )
        
        # 6. 区分场景返回结果
        if not dormitory:
            # 👉 登录场景：生成Token并返回
            access_token = create_access_token(
                subject=str(best_match.id),  # 传user_id（与auth.py一致）
                token_type="face"           # 标记为人脸登录
            )
            # 记录登录日志
            access_crud.create(db, obj_in={
                "user_id": best_match.id,
                "username": best_match.username,
                "dormitory": "登录场景",
                "status": "allowed",
                "access_type": "face",
                "access_time": datetime.now(),
                "alarm": False,
                "notes": f"人脸登录成功，相似度: {best_similarity:.3f}"
            })
            return {
                "code": 200,
                "msg": "人脸验证成功，登录凭证已生成",
                "data": {
                    "access_token": access_token,
                    "user": {
                        "id": best_match.id,
                        "student_id": best_match.student_id,
                        "username": best_match.username,
                    },
                    "similarity": best_similarity
                }
            }
        else:
            # 👉 通行场景：校验宿舍并返回通行结果
            if not best_match.dormitory or best_match.dormitory.strip() == "":
                access_record = access_crud.create(db, obj_in={
                    "user_id": best_match.id,
                    "username": best_match.username,
                    "dormitory": dormitory,
                    "status": "denied",
                    "access_type": "face",
                    "access_time": datetime.now(),
                    "alarm": True,
                    "notes": "用户未绑定宿舍，无法验证通行权限"
                })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"用户{best_match.username}（{best_match.student_id}）未绑定宿舍，请先完善信息"
                )
            
            if best_match.dormitory != dormitory:
                access_record = access_crud.create(db, obj_in={
                    "user_id": best_match.id,
                    "username": best_match.username,
                    "dormitory": dormitory,
                    "status": "denied",
                    "access_type": "face",
                    "access_time": datetime.now(),
                    "alarm": True,
                    "notes": f"宿舍不匹配：用户绑定{best_match.dormitory}，提交{dormitory}，相似度{best_similarity:.3f}"
                })
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"宿舍号错误！{best_match.username}绑定的宿舍是{best_match.dormitory}，请勿尝试非本人宿舍通行"
                )
            
            # 记录通行并返回
            access_record = access_crud.create(db, obj_in={
                "user_id": best_match.id,
                "username": best_match.username,
                "dormitory": dormitory,
                "status": "allowed",
                "access_type": "face",
                "access_time": datetime.now(),
                "alarm": False,
                "notes": f"相似度: {best_similarity:.3f}"
            })
            return {
                "code": 200,
                "msg": "人脸识别成功，允许通行",
                "data": {
                    "username": best_match.username,
                    "dormitory": dormitory,
                    "similarity": best_similarity,
                    "access_time": access_record.access_time
                }
            }
    except ValueError as e:
        # 人脸检测错误（如无人脸、图片损坏）
        access_crud.create(db, obj_in={
            "user_id": None,
            "username": "检测失败",
            "dormitory": dormitory or "未知",
            "status": "error",
            "access_type": "face",
            "access_time": datetime.now(),
            "alarm": True,
            "notes": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        # 系统异常（如数据库错误）
        access_crud.create(db, obj_in={
            "user_id": None,
            "username": "系统异常",
            "dormitory": dormitory or "未知",
            "status": "error",
            "access_type": "face",
            "access_time": datetime.now(),
            "alarm": True,
            "notes": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"人脸识别失败：{str(e)}"
        )


@router.get("/records", summary="查询通行记录（权限控制）")
def get_access_records(
    dormitory: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查询通行记录：
    - 学生：仅查看自己的记录
    - 管理员：可按宿舍、状态筛选所有记录
    """
    if current_user.role == "student":
        # 学生：仅查询自己的记录（按user_id过滤）
        records = access_crud.get_by_user_id(db, user_id=current_user.id, skip=skip, limit=limit)
        total = len(records)
    elif current_user.role == "admin":
        # 管理员：可筛选所有记录（原有逻辑不变）
        query = db.query(AccessRecord).order_by(AccessRecord.access_time.desc())
        if dormitory:
            query = query.filter(AccessRecord.dormitory == dormitory)
        if status:
            status_lower = status.lower()
            if status_lower not in VALID_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的状态类型，可选值：{VALID_STATUSES}"
                )
            query = query.filter(AccessRecord.status == status_lower)
        total = query.count()
        records = query.offset(skip).limit(limit).all()
    else:
        # 其他角色：无权限
        raise HTTPException(status_code=403, detail="无权限查看通行记录")
    
    # 格式化返回结果（保持原有结构）
    return {
        "code": 200,
        "data": {
            "total": total,
            "records": [
                {
                    "id": r.id,
                    "username": r.username,
                    "dormitory": r.dormitory,
                    "status": r.status,
                    "access_type": r.access_type,
                    "access_time": r.access_time,
                    "alarm": r.alarm,
                    "notes": r.notes
                } for r in records
            ]
        }
    }