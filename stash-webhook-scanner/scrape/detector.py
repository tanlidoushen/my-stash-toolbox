"""JAV / Non-JAV 判断逻辑。"""

import logging
import os

logger = logging.getLogger(__name__)


def _has_cjk(name):
    """检查文件名是否包含中日韩文字。"""
    return any(
        ord(c) in range(0x4e00, 0xA000)
        or ord(c) in range(0x3040, 0x3100)
        or ord(c) in range(0xAC00, 0xD800)
        for c in name
    )


def detect_japanese(paths, extract_code_fn):
    """判断文件是否为 JAV。
    优先检查文件名是否包含中日韩字符，再通过番号提取判断。
    返回 (is_japanese, first_code)。
    """
    has_cjk = any(_has_cjk(os.path.basename(p)) for p in paths)
    if has_cjk:
        logger.info("   - [检测] 类型=JAV（文件名含中日韩字符）")
        return True, None

    code = None
    for p in paths:
        code = extract_code_fn(p)
        if code:
            logger.info("   - [检测] 类型=JAV（番号=%s）", code)
            return True, code

    logger.info("   - [检测] 类型=Non-JAV（番号未匹配）")
    return False, None

def match_dir_rule(source_path, dest_path):
    """根据目录路径规则映射判断 JAV/Non-JAV。
    优先级高于文件名检测。
    返回 True(JAV), False(Non-JAV), None(未命中任何规则)。
    """
    from config import Config

    rules = getattr(Config, 'DIR_JAV_RULES', [])
    if not rules or not source_path or not dest_path:
        return None

    for rule in rules:
        sp = rule.get('source_prefix', '')
        dp = rule.get('dest_prefix', '')
        if sp and source_path.startswith(sp) and dp and dest_path.startswith(dp):
            is_jav = rule.get('is_jav')
            logger.info(
                '   - [目录规则] 命中 | source=%s | dest=%s | is_jav=%s',
                sp, dp, is_jav,
            )
            return is_jav

    return None
