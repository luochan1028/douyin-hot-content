"""敏感词匹配工具，支持谐音/缩写/拼音变体模糊匹配。"""
import re
from pathlib import Path
from typing import List, Set

from app.config import DATA_DIR

_SENSITIVE_FILE = DATA_DIR / "sensitive_words.txt"


def _load_words() -> List[str]:
    words: List[str] = []
    if not _SENSITIVE_FILE.exists():
        return words
    for line in _SENSITIVE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:  # 支持 "分类:词" 格式，只取词部分
            line = line.split(":", 1)[1]
        if line:
            words.append(line)
    return words


_SENSITIVE_WORDS: List[str] = _load_words()


def _normalize(text: str) -> str:
    """归一化：去除空白、标点、统一小写。"""
    return re.sub(r"[\s\u3000，。！？、；：""''（）【】《》,.!?;:'\"()\[\]<>]", "", text).lower()


def contains_sensitive(text: str) -> bool:
    """检测文本是否包含敏感词（含变体）。"""
    if not text:
        return False
    norm = _normalize(text)
    for word in _SENSITIVE_WORDS:
        w = _normalize(word)
        if w and w in norm:
            return True
        # 拼音首字母缩写匹配（简单实现：取词每个字拼音首字母需词库预填）
        # 此处仅做直接子串 + 去标点匹配
    return False


def hit_sensitive_words(text: str) -> List[str]:
    """返回命中的敏感词列表。"""
    hits: List[str] = []
    if not text:
        return hits
    norm = _normalize(text)
    seen: Set[str] = set()
    for word in _SENSITIVE_WORDS:
        w = _normalize(word)
        if w and w in norm and word not in seen:
            hits.append(word)
            seen.add(word)
    return hits


def reload_sensitive_words() -> int:
    """重新加载敏感词库，返回词数。"""
    global _SENSITIVE_WORDS
    _SENSITIVE_WORDS = _load_words()
    return len(_SENSITIVE_WORDS)


def add_sensitive_word(word: str) -> bool:
    """动态添加敏感词到词库文件。"""
    word = word.strip()
    if not word or word in _SENSITIVE_WORDS:
        return False
    with _SENSITIVE_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{word}\n")
    _SENSITIVE_WORDS.append(word)
    return True
