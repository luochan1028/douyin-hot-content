"""哈希工具。"""
import hashlib


def content_hash(text: str) -> str:
    """对文本生成稳定哈希，用于去重。"""
    return hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()
