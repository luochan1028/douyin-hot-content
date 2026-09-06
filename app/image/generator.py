"""图片生成器：基于 Pillow 的模板合成（零成本）+ 可插拔本地 SD。"""
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from app.config import STORAGE_DIR, DATA_DIR
from app.logger import get_logger

logger = get_logger("image.generator")

FONT_DIR = DATA_DIR / "fonts"
IMAGE_DIR = STORAGE_DIR / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920  # 9:16 竖版封面


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """加载中文字体：优先项目自带，回退系统字体。"""
    candidates = [
        FONT_DIR / ("msyhbd.ttc" if bold else "msyh.ttc"),
        # Linux 系统字体回退
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        # Windows 系统字体回退
        Path("C:/Windows/Fonts/msyhbd.ttc") if bold else Path("C:/Windows/Fonts/msyh.ttc"),
    ]
    for c in candidates:
        if c.exists():
            try:
                return ImageFont.truetype(str(c), size)
            except Exception:
                continue
    return ImageFont.load_default()


def _gradient_bg(draw, w: int, h: int, color1: Tuple[int, int, int], color2: Tuple[int, int, int]):
    for y in range(h):
        ratio = y / h
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """按字符宽度换行（中文按字）。"""
    lines = []
    cur = ""
    for ch in text:
        test = cur + ch
        if draw_text_width(font, test) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def draw_text_width(font: ImageFont.FreeTypeFont, text: str) -> int:
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]


def generate_cover(title: str, tags: Optional[list] = None,
                   brand: str = "抖音热点助手") -> Optional[Path]:
    """
    生成 1080×1920 封面图。
    返回保存路径。
    """
    tags = tags or []
    palettes = [
        ((25, 25, 112), (72, 61, 139)),
        ((220, 20, 60), (139, 0, 0)),
        ((0, 100, 0), (34, 139, 34)),
        ((47, 79, 79), (0, 139, 139)),
    ]
    color1, color2 = random.choice(palettes)

    img = Image.new("RGB", (W, H), color1)
    draw = ImageDraw.Draw(img)
    _gradient_bg(draw, W, H, color1, color2)

    # 顶部装饰条
    draw.rectangle([(0, 0), (W, 12)], fill=(255, 255, 255))

    # 标题
    title_font = _load_font(72, bold=True)
    max_w = W - 120
    lines = _wrap_text(title, title_font, max_w)
    y = 400
    for line in lines[:4]:  # 最多4行
        line_w = draw_text_width(title_font, line)
        x = (W - line_w) // 2
        draw.text((x, y), line, font=title_font, fill=(255, 255, 255))
        y += 100

    # 标签
    tag_font = _load_font(42)
    ty = H - 500
    tag_text = "  ".join(f"#{t}" for t in tags[:4])
    if tag_text:
        tag_lines = _wrap_text(tag_text, tag_font, W - 120)
        for tl in tag_lines[:2]:
            tw = draw_text_width(tag_font, tl)
            tx = (W - tw) // 2
            draw.rounded_rectangle([tx - 20, ty - 10, tx + tw + 20, ty + 60], radius=30, fill=(255, 255, 255, 200))
            draw.text((tx, ty), tl, font=tag_font, fill=color1)
            ty += 80

    # 水印
    wm_font = _load_font(36)
    wm = brand
    wm_w = draw_text_width(wm_font, wm)
    draw.text(((W - wm_w) // 2, H - 120), wm, font=wm_font, fill=(255, 255, 255, 180))

    # 保存
    fname = f"cover_{datetime.now():%Y%m%d_%H%M%S}_{random.randint(1000,9999)}.jpg"
    out_path = IMAGE_DIR / fname
    img.save(out_path, "JPEG", quality=88, optimize=True)

    # 确保 <= 5MB
    if out_path.stat().st_size > 5 * 1024 * 1024:
        img.save(out_path, "JPEG", quality=70, optimize=True)

    logger.info("封面图已生成: %s (%.1f KB)", out_path, out_path.stat().st_size / 1024)
    return out_path


def generate_image_sd(prompt: str) -> Optional[Path]:
    """可插拔：本地 Stable Diffusion（需配置 SD_BASE_URL）。未配置返回 None。"""
    from app.config import settings
    if not settings.SD_BASE_URL:
        return None
    try:
        import httpx, base64
        resp = httpx.post(f"{settings.SD_BASE_URL}/sdapi/v1/txt2img", json={"prompt": prompt, "steps": 20}, timeout=120)
        data = resp.json()
        img_b64 = data["images"][0]
        img = Image.open(__import__("io").BytesIO(base64.b64decode(img_b64)))
        img = img.resize((W, H))
        fname = f"sd_{datetime.now():%Y%m%d_%H%M%S}.png"
        out = IMAGE_DIR / fname
        img.save(out, "PNG")
        return out
    except Exception as e:
        logger.warning("SD 生成失败: %s", e)
        return None
