"""视频生成器：FFmpeg 轻量合成（零成本）。"""
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings, STORAGE_DIR, DATA_DIR
from app.logger import get_logger

logger = get_logger("video.generator")

VIDEO_DIR = STORAGE_DIR / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920

# 项目自带中文字体（跨平台，不依赖系统字体）
FONT_PATH = DATA_DIR / "fonts" / "msyh.ttc"


def _ffmpeg_font_path() -> str:
    """获取跨平台的 FFmpeg drawtext 字体路径（已转义特殊字符）。"""
    p = str(FONT_PATH.resolve()).replace("\\", "/")
    # FFmpeg filtergraph 中冒号是参数分隔符，需转义
    return p.replace(":", r"\:")


def _ffmpeg(*args) -> subprocess.CompletedProcess:
    cmd = [settings.FFMPEG_PATH, "-y", *args]
    logger.debug("ffmpeg cmd: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")


def _ffprobe(path: str) -> dict:
    cmd = [settings.FFPROBE_PATH, "-v", "quiet", "-print_format", "json", "-show_streams", path]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        return {}
    return json.loads(r.stdout)


def _escape_text(text: str) -> str:
    """转义 ffmpeg drawtext 特殊字符。"""
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace('"', '\\"')


def generate_video(image_path: str, title: str, body: str,
                   duration: int = 20, tags: Optional[list] = None) -> Optional[dict]:
    """
    合成短视频：图片 + 字幕 + BGM。
    返回 {video_path, cover_path, duration, width, height, has_audio}。
    """
    tags = tags or []
    fname = f"video_{datetime.now():%Y%m%d_%H%M%S}.mp4"
    out_path = VIDEO_DIR / fname
    cover_path = VIDEO_DIR / f"{fname}.cover.jpg"

    # 字幕文本：标题 + 正文前两行
    subtitle = _escape_text(title[:30])
    body_short = _escape_text(body.replace("\n", " ")[:60])

    # 使用项目自带中文字体（跨平台）
    font = _ffmpeg_font_path()

    # drawtext 滤镜：标题居中上方，正文居中下方
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"drawtext=fontfile='{font}':text='{subtitle}':"
        f"fontsize=64:fontcolor=white:x=(w-text_w)/2:y=h*0.15,"
        f"drawtext=fontfile='{font}':text='{body_short}':"
        f"fontsize=42:fontcolor=white:x=(w-text_w)/2:y=h*0.30"
    )

    # 使用 sine 生成 BGM（零成本，免版权）
    bgm_filter = f"anullsrc=r=44100:cl=stereo"

    try:
        # 主合成
        r = _ffmpeg(
            "-loop", "1", "-i", image_path,
            "-f", "lavfi", "-i", bgm_filter,
            "-t", str(duration),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-b:v", "3M",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(out_path),
        )
        if r.returncode != 0:
            logger.error("视频合成失败: %s", r.stderr[-500:])
            return None

        # 截取封面（前 3 秒的一帧）
        rc = _ffmpeg("-i", str(out_path), "-ss", "00:00:01", "-vframes", "1", str(cover_path))
        if rc.returncode != 0:
            logger.warning("封面截取失败: %s", rc.stderr[-300:])
            cover_path = None

        # 探测视频信息
        info = _ffprobe(str(out_path))
        vstream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
        astream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)

        result = {
            "video_path": str(out_path),
            "cover_path": str(cover_path) if cover_path else "",
            "duration": float(vstream.get("duration", duration)),
            "width": int(vstream.get("width", W)),
            "height": int(vstream.get("height", H)),
            "has_audio": astream is not None,
        }
        logger.info("视频生成成功: %s", result)
        return result
    except Exception as e:
        logger.error("视频生成异常: %s", e)
        return None
