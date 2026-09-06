"""文案质量自检。"""
import re
from dataclasses import dataclass, field
from typing import List

from app.copywriting.templates import BANNED_WORDS
from app.utils.sensitive import contains_sensitive


@dataclass
class CheckResult:
    passed: bool
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"passed": self.passed, "issues": self.issues}


def self_check(title: str, body: str, tags: List[str], cta: str) -> CheckResult:
    """
    文案质量自检规则：
    - 总字数（标题+正文）100-300
    - 含互动引导语（cta 非空）
    - 标签数量 3-5
    - 无违规词/极限词
    - 无敏感词
    - 无重复句式（简单检测连续相同句）
    """
    issues: List[str] = []
    full_text = f"{title}。{body}"
    char_count = len(full_text)

    if char_count < 100:
        issues.append(f"字数不足: {char_count} < 100")
    elif char_count > 300:
        issues.append(f"字数超限: {char_count} > 300")

    if not cta or len(cta.strip()) < 5:
        issues.append("缺少互动引导语")

    if len(tags) < 3:
        issues.append(f"标签数量不足: {len(tags)} < 3")
    elif len(tags) > 5:
        issues.append(f"标签数量超限: {len(tags)} > 5")

    for bw in BANNED_WORDS:
        if bw in full_text:
            issues.append(f"包含极限词: {bw}")
            break

    if contains_sensitive(full_text):
        issues.append("包含敏感词")

    # 重复句式检测：连续两个句子相同
    sentences = re.split(r"[。！？!?]", body)
    seen = set()
    for s in sentences:
        s = s.strip()
        if len(s) > 4 and s in seen:
            issues.append("存在重复句式")
            break
        seen.add(s)

    return CheckResult(passed=len(issues) == 0, issues=issues)
