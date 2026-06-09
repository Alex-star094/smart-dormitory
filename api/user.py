from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import base64
import numpy as np
import io
import re

from utils.face_utils import extract_face_embedding, embedding_to_base64, preprocess_image_for_face_detection
from crud.user import user_crud
from api.auth import get_current_user, require_admin
from utils.db import get_db
from models.user import User

router = APIRouter()

@router.get("/profile", summary="获取当前用户信息")
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_info = db.query(User).filter(User.id == current_user.id).first()
    """获取当前登录用户的个人信息"""
    return {
        "code": 200,
        "msg": "获取成功",
        "data": {
            "id": current_user.id,
            "student_id": current_user.student_id,
            "username": current_user.username,
            "role": current_user.role,  # 直接使用role字段值
            "dormitory": current_user.dormitory,
            "phone": current_user.phone,
            "has_face": bool(current_user.face_encoding)
        }
    }

@router.put("/profile", summary="更新个人信息")
def update_profile(
    dormitory: Optional[str] = None,
    phone: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新当前用户的宿舍号和手机号"""
    if not dormitory and not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少需要修改一个字段（宿舍号或手机号）"
        )

    # 手机号格式校验
    if phone and not re.match(r'^1[3-9]\d{9}$', phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="手机号格式不正确（需为11位有效号码）"
        )

    # 宿舍号格式简单校验（可根据实际规则调整）
    if dormitory and not re.match(r'^[A-Za-z0-9-]+$', dormitory):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="宿舍号格式不正确（仅支持字母、数字和连字符）"
        )

    user = user_crud.update_user_info(
        db,
        user_id=current_user.id,
        dormitory=dormitory,
        phone=phone
    )

    return {
        "code": 200,
        "msg": "更新成功",
        "data": {
            "dormitory": user.dormitory,
            "phone": user.phone
        }
    }

@router.post("/profile/face", summary="上传用户人脸照片")
async def upload_user_face(
    face_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """用户上传人脸照片进行注册"""
    try:
        # 验证文件类型
        if not face_image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请上传图片文件"
            )

        # 读取图片文件
        contents = await face_image.read()

        # 预处理图片并提取人脸特征
        from utils.face_utils import preprocess_image_for_face_detection, extract_face_embedding, embedding_to_base64
        processed_contents = preprocess_image_for_face_detection(contents)
        face_embedding = extract_face_embedding(processed_contents)
        face_encoding_base64 = embedding_to_base64(face_embedding)

        # 更新用户人脸信息
        user_crud.update_face_encoding(db, user_id=current_user.id, face_encoding=face_encoding_base64)

        return {
            "code": 200,
            "msg": "人脸上传成功",
            "data": {
                "has_face": True
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"人脸检测失败：{str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"人脸上传失败：{str(e)}"
        )

@router.get("/list", summary="管理员获取用户列表")
def get_user_list(
    role: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理员查询用户列表，支持按角色筛选和分页"""
    # 限制分页参数范围，防止恶意请求
    if skip < 0:
        skip = 0
    if limit < 1 or limit > 100:
        limit = 20

    if role:
        # 直接使用字符串角色进行筛选
        total = user_crud.count_by_role(db, role=role)
        users = user_crud.get_by_role(db, role=role, skip=skip, limit=limit)
    else:
        total = user_crud.count_multi(db)
        users = user_crud.get_multi(db, skip=skip, limit=limit)

    return {
        "code": 200,
        "data": {
            "total": total,  # 返回总条数而非当前页数量
            "users": [
                {
                    "id": user.id,
                    "student_id": user.student_id,
                    "username": user.username,
                    "role": user.role,  # 直接使用role字段值
                    "dormitory": user.dormitory,
                    "phone": user.phone,
                    "is_active": user.is_active,
                    "created_at": user.created_at
                } for user in users
            ]
        }
    }
