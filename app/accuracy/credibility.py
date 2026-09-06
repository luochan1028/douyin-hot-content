"""话题可信度评分与合规校验。"""
from dataclasses import dataclass
from typing import List, Tuple

from app.accuracy.classifier import classify
from app.utils.sensitive import contains_sensitive
from app.config import settings, account_tags
from app.logger import get_logger

logger = get_logger("accuracy.credibility")

# 数据源权威性分级
SOURCE_AUTHORITY = {
    "douyin": 1.0,
    "baidu": 0.8,
    "toutiao": 0.8,
    "bilibili": 0.8,
    "weibo": 0.5,
    "zhihu": 0.5,
}

# 权威媒体关键词（用于真实性背书）
AUTHORITY_MEDIA_KEYWORDS = ["人民日报", "新华社", "央视", "中央电视台", "人民网", "新华网", "光明日报"]


@dataclass
class CredibilityResult:
    score: float  # 0-100
    decision: str  # approved / review / rejected
    category: str
    match_score: float
    is_sensitive: bool
    source_authority: float
    cross_valid: float
    reasons: List[str]


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union) if union else 0.0


def _topic_keywords(word: str) -> set:
    """简单分词：按字符 2-gram + 完整词。"""
    kws = {word}
    if len(word) >= 2:
        for i in range(len(word) - 1):
            kws.add(word[i:i + 2])
    return kws


def account_match_score(word: str, category: str = "") -> float:
    """计算话题与账号定位的匹配度（0-100）。"""
    tags = account_tags()
    account_category = settings.ACCOUNT_CATEGORY
    if not word:
        return 0.0
    word_lower = word.lower()
    # 命中账号标签数量
    hit_tags = 0
    for t in tags:
        if t and (t.lower() in word_lower or word_lower in t.lower()):
            hit_tags += 1
    tag_score = min(40.0, hit_tags * 15.0)
    # 分类匹配加成
    cat_score = 0.0
    if category and account_category:
        if category == account_category:
            cat_score = 45.0
        elif category in ("科技",) and account_category in ("科技",):
            cat_score = 45.0
        else:
            cat_score = 10.0
    base = 15.0
    score = min(100.0, base + tag_score + cat_score)
    return round(score, 2)


def evaluate_credibility(word: str, source: str, source_count: int = 1,
                         heat_value: float = 0.0) -> CredibilityResult:
    """
    综合可信度评分。
    维度：数据源权威性 30% + 交叉验证 25% + 分类准确性 15% + 敏感词 15% + 账号匹配度 15%
    """
    reasons: List[str] = []

    # 1. 敏感词一票否决
    is_sensitive = contains_sensitive(word)
    sensitive_score = 0.0 if is_sensitive else 100.0
    if is_sensitive:
        reasons.append("命中敏感词")

    # 2. 数据源权威性
    src_auth = SOURCE_AUTHORITY.get(source, 0.5) * 100
    reasons.append(f"数据源权威性: {SOURCE_AUTHORITY.get(source, 0.5)}")

    # 3. 交叉验证（多源共现）
    if source_count >= 3:
        cross_valid = 100.0
    elif source_count == 2:
        cross_valid = 70.0
    else:
        cross_valid = 30.0
    reasons.append(f"多源共现: {source_count} 个数据源")

    # 4. 分类准确性（能归入明确类别得高分）
    category = classify(word)
    cat_score = 100.0 if category != "其他" else 40.0
    reasons.append(f"分类: {category}")

    # 5. 账号匹配度（结合分类）
    match = account_match_score(word, category)

    # 综合评分
    score = (
        src_auth * 0.30
        + cross_valid * 0.25
        + cat_score * 0.15
        + sensitive_score * 0.15
        + match * 0.15
    )
    score = round(min(100.0, max(0.0, score)), 2)

    # 决策
    if is_sensitive or match < 60:
        decision = "rejected"
        if match < 60:
            reasons.append(f"账号匹配度过低: {match}")
    elif score < settings.CREDIBILITY_REVIEW:
        decision = "rejected"
    elif score < settings.CREDIBILITY_PASS:
        decision = "review"
    else:
        decision = "approved"

    return CredibilityResult(
        score=score,
        decision=decision,
        category=category,
        match_score=match,
        is_sensitive=is_sensitive,
        source_authority=src_auth,
        cross_valid=cross_valid,
        reasons=reasons,
    )
