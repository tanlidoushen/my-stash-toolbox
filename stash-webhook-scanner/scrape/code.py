"""番号提取、格式化、黑名单过滤。"""

import logging
import re

logger = logging.getLogger(__name__)


def normalize_japanese_code(code):
    """将番号格式化为通用格式：ABC123 -> ABC-123，数字部分补零。"""
    if not code:
        return None
    if "-" in code:
        return code.upper()
    match = re.match(r"([A-Za-z]+)(\d+)([A-Za-z]?)", code)
    if match:
        letters = match.group(1).upper()
        numbers = match.group(2)
        suffix = match.group(3).upper() if match.group(3) else ""
        numbers_clean = str(int(numbers)).zfill(3) if numbers else "000"
        normalized = "%s-%s" % (letters, numbers_clean)
        if suffix:
            normalized += "-%s" % suffix
        return normalized
    return code.upper()


def extract_japanese_code(file_path, western_blacklist=None):
    """从文件路径中提取日本番号并格式化。
    匹配到的番号前缀如果在欧美黑名单中则视为 None。
    """
    from config import Config

    blacklist = western_blacklist or Config.WESTERN_CODE_BLACKLIST

    patterns = [
        r"[A-Za-z]{2,6}-?\d{2,5}",
        r"[A-Za-z]{3,6}\d{2,5}",
        r"[A-Za-z]{2,6}-\d{2,5}[A-Za-z]?",
    ]

    if "\\" in file_path:
        filename = file_path.split("\\")[-1].upper()
    else:
        filename = file_path.split("/")[-1].upper()

    for pattern in patterns:
        matches = re.findall(pattern, filename, re.IGNORECASE)
        if matches:
            code = max(matches, key=len)
            code = re.sub(r"[^A-Z0-9-]", "", code.upper())
            if len(code) >= 4:
                prefix = code.split("-")[0] if "-" in code else "".join(filter(str.isalpha, code))
                if prefix in blacklist:
                    logger.debug("黑名单命中 | 前缀=%s | 路径=%s", prefix, file_path)
                    return None
                return normalize_japanese_code(code)
    return None
