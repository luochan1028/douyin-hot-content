"""AI 文案生成器：模板引擎（默认，零成本）+ 可插拔 Ollama。"""
import random
from dataclasses import dataclass
from typing import List, Optional

from app.copywriting.templates import get_template, CTA_POOL
from app.copywriting.selfcheck import self_check, CheckResult
from app.config import settings
from app.logger import get_logger

logger = get_logger("copywriting.generator")


@dataclass
class Copywriting:
    title: str
    body: str
    tags: List[str]
    cta: str
    style: str
    need_human_polish: bool = False

    @property
    def full_text(self) -> str:
        return f"{self.title}\n{self.body}\n{self.cta}\n{' '.join('#' + t for t in self.tags)}"


def _fill_template(template: dict, word: str, tags: List[str]) -> tuple:
    title = template["title"].format(word=word)
    body = template["body"].format(word=word)
    cta_raw = template.get("cta") or random.choice(CTA_POOL)
    try:
        cta = cta_raw.format(word=word)
    except (KeyError, IndexError):
        cta = cta_raw
    return title, body, cta


def generate_copy(word: str, tags: Optional[List[str]] = None,
                  style: Optional[str] = None, max_retry: int = 3) -> Copywriting:
    """
    生成文案并自检。失败重试最多 max_retry 次，仍失败则标记需人工润色。
    """
    style = style or settings.COPYWRITING_STYLE
    tags = tags or [word]
    # 确保标签 3-5 个
    if len(tags) < 3:
        tags = tags + [settings.ACCOUNT_CATEGORY, "热点"]
    tags = tags[:5]

    for attempt in range(1, max_retry + 1):
        template = get_template(style)
        title, body, cta = _fill_template(template, word, tags)
        result = self_check(title, body, tags, cta)
        if result.passed:
            logger.info("文案生成成功（第 %d 次尝试）: %s", attempt, word)
            return Copywriting(title=title, body=body, tags=tags, cta=cta, style=style)
        logger.warning("文案自检失败（第 %d 次）: %s", attempt, result.issues)

    # 重试耗尽，标记需人工润色
    logger.warning("文案重试 %d 次仍未通过，标记需人工润色: %s", max_retry, word)
    template = get_template(style)
    title, body, cta = _fill_template(template, word, tags)
    return Copywriting(title=title, body=body, tags=tags, cta=cta, style=style, need_human_polish=True)


async def generate_copy_ollama(word: str, tags: Optional[List[str]] = None,
                               style: Optional[str] = None) -> Optional[Copywriting]:
    """
    可插拔：通过本地 Ollama 生成文案（需用户自行安装 Ollama 并配置 OLLAMA_BASE_URL）。
    未配置时返回 None，回退到模板引擎。
    """
    if not settings.OLLAMA_BASE_URL:
        return None
    try:
        import httpx
        prompt = (
            f"你是一个抖音短视频文案写手。请围绕热点话题「{word}」，"
            f"以「{style or settings.COPYWRITING_STYLE}」风格撰写短视频文案。"
            f"要求：1. 标题吸引眼球；2. 正文100-300字；3. 包含互动引导语；"
            f"4. 给出3-5个话题标签。输出格式：标题\\n正文\\n互动语\\n标签（逗号分隔）。"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            data = resp.json()
            text = data.get("response", "")
            # 简单解析
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if len(lines) >= 4:
                return Copywriting(
                    title=lines[0], body="\n".join(lines[1:-2]),
                    tags=[t.strip("# ") for t in lines[-1].split(",")],
                    cta=lines[-2], style=style or "ollama",
                )
    except Exception as e:
        logger.warning("Ollama 生成失败，回退模板引擎: %s", e)
    return None
