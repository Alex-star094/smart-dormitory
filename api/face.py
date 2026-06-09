# api/face.py
import logging

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from crud.user import user_crud
from api.auth import require_admin
from utils.db import get_db
from utils.face_utils import (
    extract_face_embedding,
    embedding_to_base64,
    base64_to_embedding,
    compare_faces,
)
from models.user import User
from config import settings

logger = logging.getLogger("face_api")
router = APIRouter(tags=["人脸管理"])

@router.post("/register", summary="人脸信息录入（严格唯一绑定）")
async def face_register(
    student_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # 1. 校验文件类型
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="仅支持图片文件（jpg/png）")
    
    # 2. 查询用户
    user = user_crud.get_by_student_id(db, student_id=student_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"学号{student_id}不存在")
    
    # 3. 检查当前用户是否已绑定人脸（拦截重复注册）
    if user.face_encoding is not None and user.face_encoding != "":
        raise HTTPException(status_code=400, detail=f"学号{student_id}（{user.username}）已绑定人脸，不可重复注册")
    
    # 4. 提取新上传的人脸特征
    try:
        image_bytes = await file.read()
        new_embedding = extract_face_embedding(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"人脸提取失败：{str(e)}")
    
    # 5. 核心：双保险校验（特征比对 + 字符串查重），严格防重复
    all_users = db.query(User).all()  # 查询所有用户
    # 筛选出已绑定人脸的用户（非空且非空字符串）
    existing_users = [u for u in all_users if u.face_encoding is not None and u.face_encoding.strip() != ""]
    logger.info(f"开始校验新人脸是否已绑定（当前已绑定人数：{len(existing_users)}）")

    # 先将新提取的人脸特征转成Base64字符串（用于直接查重）
    new_face_encoding = embedding_to_base64(new_embedding)

    # 第一步：直接校验face_encoding字符串是否重复（最直接的方式）
    duplicate_user = db.query(User).filter(User.face_encoding == new_face_encoding).first()
    if duplicate_user:
        logger.info(f"字符串查重命中重复：{duplicate_user.student_id}（{duplicate_user.username}）")
        raise HTTPException(
        status_code=400,
        detail=f"该人脸已绑定学号{duplicate_user.student_id}（{duplicate_user.username}），不可重复绑定"
    )

    # 第二步：特征比对（兜底，防止字符串意外不一致的情况）
    threshold = settings.FACE_MATCH_THRESHOLD
    for existing_user in existing_users:
        try:
            # 解码已存储的人脸特征
            stored_embedding = base64_to_embedding(existing_user.face_encoding)
            # 比对新特征与已存储特征
            is_match, similarity = compare_faces(new_embedding, stored_embedding, threshold)
            logger.debug(f"比对：{existing_user.student_id} vs {student_id} → 相似度={similarity}，匹配={is_match}")
        
        # 相似度达标则拦截
            if is_match:
                raise HTTPException(
                    status_code=400,
                    detail=f"该人脸已绑定学号{existing_user.student_id}（{existing_user.username}），相似度={similarity}，不可重复绑定"
                )
        except Exception as e:
            print(f"比对用户{existing_user.student_id}失败：{e}")
            continue
    
    # 6. 所有校验通过，绑定人脸
    face_encoding = embedding_to_base64(new_embedding)
    user_crud.update_face_encoding(db, user_id=user.id, face_encoding=face_encoding)
    
    return {
        "code": 200,
        "msg": f"学号{student_id}（{user.username}）人脸绑定成功",
        "data": {"student_id": student_id, "username": user.username}
    }