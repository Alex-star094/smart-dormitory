import base64
import io
import logging

import numpy as np
from PIL import Image

from utils.logger import setup_logger

logger = setup_logger("face_utils")

# 延迟导入cv2
try:
    import cv2
    CV2_AVAILABLE = True
except (ImportError, AttributeError):
    CV2_AVAILABLE = False
    cv2 = None

# 延迟导入insightface（核心人脸库）
try:
    import insightface
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except (ImportError, AttributeError):
    INSIGHTFACE_AVAILABLE = False
    insightface = None
    FaceAnalysis = None

# 全局变量：人脸模型实例 + 模拟模式标记（增加保护机制）
face_app = None
use_mock = False  # 默认为False，仅在模型加载失败时设为True


def get_face_app():
    """
    获取或初始化人脸分析模型（修复模型加载失败后的状态同步）
    返回：FaceAnalysis实例（正常）或 "mock"（异常）
    """
    global face_app, use_mock
    if face_app is not None:
        return face_app

    # 若insightface不可用，直接进入模拟模式
    if not INSIGHTFACE_AVAILABLE:
        logger.error("insightface库未安装，无法进行真实人脸比对！")
        use_mock = True
        face_app = "mock"
        return face_app

    # 尝试加载insightface模型（buffalo_l为通用模型）
    try:
        logger.info("正在初始化insightface人脸模型...")
        face_app = FaceAnalysis(name="buffalo_l")
        # 强制使用CPU（避免GPU显存问题，适配更多环境）
        face_app.prepare(ctx_id=-1, det_size=(640, 640))  
        logger.info("✅ insightface模型初始化成功")
        use_mock = False  # 模型加载成功，关闭模拟模式
        return face_app
    except Exception as e:
        logger.error(f"模型加载失败：{str(e)}")
        logger.warning("已切换到模拟模式（仅用于测试，无真实人脸比对功能！）")
        use_mock = True
        face_app = "mock"
        return face_app


def extract_face_embedding(image_data: bytes) -> np.ndarray:
    """
    提取人脸特征向量（修复：模拟模式下抛错，禁止无效绑定）
    Args:
        image_data: 图片二进制数据
    Returns:
        512维人脸特征向量（insightface正常输出）
    Raises:
        ValueError: 模拟模式/无人脸/多人脸/提取失败时抛错
    """
    global use_mock

    # 核心修复1：模拟模式下禁止提取特征（避免无效绑定）
    if use_mock:
        raise ValueError(
            "❌ 无法提取人脸特征：当前处于模拟模式（insightface模型加载失败），"
            "请安装insightface库并确保模型加载正常（执行：pip install insightface）"
        )

    # 核心修复2：确保insightface可用（双重校验）
    if not INSIGHTFACE_AVAILABLE or face_app == "mock":
        use_mock = True
        raise ValueError(
            "❌ 人脸提取失败：insightface库未安装或模型未初始化，"
            "请先安装依赖（pip install insightface）并重启服务"
        )

    try:
        # 图片格式转换（PIL → RGB → numpy数组，适配insightface输入）
        image = Image.open(io.BytesIO(image_data))
        if image.mode != "RGB":
            image = image.convert("RGB")
        img_array = np.array(image)

        # 检测人脸（insightface核心接口）
        app = get_face_app()
        faces = app.get(img_array)

        # 校验人脸数量（仅允许单张人脸）
        if len(faces) == 0:
            raise ValueError("未检测到人脸，请上传包含清晰单人脸的图片（避免遮挡、侧脸）")
        if len(faces) > 1:
            raise ValueError(f"检测到{len(faces)}张人脸，请上传仅包含一张人脸的图片")

        # 返回512维特征向量（insightface标准输出）
        return faces[0].embedding

    except Exception as e:
        # 捕获所有异常，明确提示用户
        raise ValueError(f"人脸特征提取失败：{str(e)}（建议检查图片清晰度或格式）")


def embedding_to_base64(embedding: np.ndarray) -> str:
    """
    将人脸特征向量转换为Base64字符串（修复：增加向量维度校验）
    Args:
        embedding: 512维特征向量（insightface输出）
    Returns:
        Base64编码字符串
    Raises:
        ValueError: 向量维度错误时抛错
    """
    # 校验向量维度（确保是insightface生成的512维向量）
    if embedding.shape != (512,):
        raise ValueError(f"无效的人脸特征向量：需为512维，当前为{embedding.shape[0]}维")

    try:
        # numpy数组 → bytes → Base64（保留精度）
        embedding_bytes = embedding.tobytes()
        return base64.b64encode(embedding_bytes).decode("utf-8")
    except Exception as e:
        raise ValueError(f"特征向量编码失败：{str(e)}")


def base64_to_embedding(embedding_base64: str) -> np.ndarray:
    """
    将Base64字符串解码为人脸特征向量（修复：增加维度校验）
    Args:
        embedding_base64: Base64编码字符串
    Returns:
        512维特征向量
    Raises:
        ValueError: 解码失败或维度错误时抛错
    """
    try:
        # Base64 → bytes → numpy数组（指定float32精度，匹配insightface）
        embedding_bytes = base64.b64decode(embedding_base64)
        embedding = np.frombuffer(embedding_bytes, dtype=np.float32)

        # 校验维度（避免无效特征导致比对失败）
        if embedding.shape != (512,):
            raise ValueError(f"解码后的特征向量维度错误：需为512维，当前为{embedding.shape[0]}维")

        return embedding
    except Exception as e:
        raise ValueError(f"人脸特征解码失败：{str(e)}（可能是特征格式损坏或非本系统生成）")


def compare_faces(
    embedding1: np.ndarray, 
    embedding2: np.ndarray, 
    threshold: float = 0.85  # 修复：insightface推荐阈值（余弦相似度）
) -> tuple[bool, float]:
    """
    比较两个人脸特征向量的相似度（适配insightface特性）
    Args:
        embedding1: 新上传人脸的特征向量
        embedding2: 数据库中存储的特征向量
        threshold: 相似度阈值（insightface推荐0.85，值越大越严格）
    Returns:
        (是否匹配, 余弦相似度分数)
    Raises:
        ValueError: 模拟模式/向量维度错误/比对失败时抛错
    """
    global use_mock

    # 核心修复3：模拟模式下禁止比对（避免无效结果）
    if use_mock:
        raise ValueError(
            "❌ 无法进行人脸比对：当前处于模拟模式（insightface模型加载失败），"
            "请安装依赖并确保模型正常加载"
        )

    try:
        # 校验向量维度（确保两者均为512维）
        if embedding1.shape != (512,) or embedding2.shape != (512,):
            raise ValueError(
                f"特征向量维度不匹配：需均为512维，"
                f"当前分别为{embedding1.shape[0]}维和{embedding2.shape[0]}维"
            )

        # 计算余弦相似度（insightface标准比对方法）
        # 公式：cosθ = (a·b) / (||a|| × ||b||)，范围[-1,1]，值越大越相似
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        # 避免除以0（理论上特征向量不会全为0）
        if norm1 == 0 or norm2 == 0:
            raise ValueError("无效的特征向量（存在全零向量）")
        
        similarity = dot_product / (norm1 * norm2)

        # 判断是否匹配（阈值设为0.85，insightface推荐值，可根据需求调整）
        is_match = similarity >= threshold
        return is_match, round(float(similarity), 4)  # 保留4位小数，便于日志查看

    except Exception as e:
        raise ValueError(f"人脸比对失败：{str(e)}")


def preprocess_image_for_face_detection(image_data: bytes) -> bytes:
    """
    预处理图片（提高人脸检测成功率，修复：增加格式校验）
    Args:
        image_data: 原始图片二进制数据
    Returns:
        处理后的图片二进制数据（JPG格式）
    Raises:
        ValueError: 图片读取/编码失败时抛错
    """
    # 若OpenCV不可用，返回原图（但提示风险）
    if not CV2_AVAILABLE:
        logger.warning("OpenCV未安装，图片预处理功能失效（可能影响人脸检测成功率）")
        return image_data

    try:
        # 读取图片（处理JPG/PNG等格式）
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("无法读取图片（可能是格式损坏或非图片文件）")

        # 转换为RGB（insightface要求输入为RGB格式）
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # 调整图片大小（避免过大图片导致内存溢出，最大边长1024）
        height, width = img_rgb.shape[:2]
        max_size = 1024
        if max(height, width) > max_size:
            scale = max_size / max(height, width)
            new_size = (int(width * scale), int(height * scale))
            img_rgb = cv2.resize(img_rgb, new_size, interpolation=cv2.INTER_AREA)

        # 编码为JPG格式（统一输出格式，减少后续错误）
        success, encoded_img = cv2.imencode(".jpg", cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
        if not success:
            raise ValueError("图片编码失败（无法转换为JPG格式）")

        return encoded_img.tobytes()

    except Exception as e:
        raise ValueError(f"图片预处理失败：{str(e)}（建议上传标准JPG/PNG图片，大小不超过5MB）")


# 初始化时自动检查模型状态（提前暴露问题，避免运行时报错）
get_face_app()