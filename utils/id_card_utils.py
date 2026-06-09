import re
from datetime import datetime

def validate_id_card_format(id_card: str) -> bool:
    """
    基础校验：验证身份证号格式（15位纯数字 或 18位数字+X/x）
    返回：True（格式合法）/ False（格式非法）
    """
    if not isinstance(id_card, str):
        return False
    # 正则表达式：15位纯数字 或 18位（前17位数字，最后1位数字/X/x）
    id_card_pattern = r'^(?:\d{15}|\d{17}[\dXx])$'
    return re.match(id_card_pattern, id_card) is not None

def normalize_id_card(id_card: str) -> str:
    """
    规范化身份证号：18位时统一转为大写X，15位补全为18位（按GB标准补全出生日期）
    返回：规范化后的18位身份证号
    """
    id_card = id_card.strip()
    # 18位：统一X为大写
    if len(id_card) == 18:
        return id_card.upper()
    # 15位：补全为18位（出生日期补"19"，并计算校验码）
    elif len(id_card) == 15:
        # 15位转18位：出生日期6位→8位（19XX年，适用于1900-1999年出生）
        birth_year = f"19{id_card[6:8]}"
        birth_month = id_card[8:10]
        birth_day = id_card[10:12]
        # 前17位：地址码（6）+ 补全出生日期（8）+ 顺序码（3）
        id_card_17 = f"{id_card[:6]}{birth_year}{birth_month}{birth_day}{id_card[12:]}"
        # 计算校验码并拼接为18位
        check_code = calculate_id_card_check_code(id_card_17)
        return f"{id_card_17}{check_code}"
    return ""

def calculate_id_card_check_code(id_card_17: str) -> str:
    """
    根据18位身份证前17位计算校验码（符合GB 11643-1999标准）
    """
    if len(id_card_17) != 17 or not id_card_17.isdigit():
        return ""
    # 加权因子（GB标准）
    weight_factors = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    # 校验码对应表（余数0→1，1→0，2→X，...，10→2）
    check_code_map = "10X98765432"
    # 计算前17位加权和
    total = sum(int(id_card_17[i]) * weight_factors[i] for i in range(17))
    # 取模11得到余数，对应校验码
    remainder = total % 11
    return check_code_map[remainder]

def is_valid_id_card(id_card: str) -> tuple[bool, str]:
    """
    完整校验：格式+校验码+出生日期合法性
    返回：(是否合法, 错误信息)
    """
    # 1. 基础格式校验
    if not validate_id_card_format(id_card):
        return False, "身份证号格式无效（需为15位纯数字或18位数字+X/x）"
    
    # 2. 规范化处理
    normalized_id = normalize_id_card(id_card)
    if len(normalized_id) != 18:
        return False, "身份证号规范化失败"
    
    # 3. 校验码验证（仅18位需要）
    id_17 = normalized_id[:17]
    actual_check_code = normalized_id[-1]
    expected_check_code = calculate_id_card_check_code(id_17)
    if actual_check_code != expected_check_code:
        return False, "身份证号校验码错误，可能为无效号码"
    
    # 4. 出生日期合法性校验（从18位中提取第7-14位：YYYYMMDD）
    birth_date_str = normalized_id[6:14]
    try:
        birth_date = datetime.strptime(birth_date_str, "%Y%m%d")
        # 出生日期不能超过当前时间，且不能早于1900年
        if birth_date > datetime.now() or birth_date.year < 1900:
            return False, "身份证号出生日期无效"
    except ValueError:
        return False, "身份证号出生日期格式错误"
    
    return True, "身份证号合法"