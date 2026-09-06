"""多渠道通知：钉钉、企业微信 Webhook、邮件。"""
import json
import smtplib
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings
from app.utils.http import sync_post
from app.logger import get_logger

logger = get_logger("notify.notifier")


def send_dingtalk(text: str) -> bool:
    if not settings.DINGTALK_WEBHOOK:
        return False
    try:
        payload = {"msgtype": "text", "text": {"content": text}}
        resp = sync_post(settings.DINGTALK_WEBHOOK, json=payload, timeout=10)
        ok = resp.status_code == 200 and resp.json().get("errcode", -1) == 0
        logger.info("钉钉通知: %s", "成功" if ok else f"失败 {resp.status_code}")
        return ok
    except Exception as e:
        logger.error("钉钉通知异常: %s", e)
        return False


def send_wecom(text: str) -> bool:
    if not settings.WECOM_WEBHOOK:
        return False
    try:
        payload = {"msgtype": "text", "text": {"content": text}}
        resp = sync_post(settings.WECOM_WEBHOOK, json=payload, timeout=10)
        ok = resp.status_code == 200 and resp.json().get("errcode", -1) == 0
        logger.info("企业微信通知: %s", "成功" if ok else f"失败 {resp.status_code}")
        return ok
    except Exception as e:
        logger.error("企业微信通知异常: %s", e)
        return False


def send_email(subject: str, text: str) -> bool:
    if not (settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_TO):
        return False
    try:
        msg = MIMEText(text, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.SMTP_TO
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.sendmail(settings.SMTP_USER, [settings.SMTP_TO], msg.as_string())
        logger.info("邮件通知成功")
        return True
    except Exception as e:
        logger.error("邮件通知异常: %s", e)
        return False


def notify(title: str, detail: str) -> dict:
    """向所有已配置渠道发送通知。"""
    text = f"【{title}】\n{detail}"
    results = {
        "dingtalk": send_dingtalk(text),
        "wecom": send_wecom(text),
        "email": send_email(title, detail),
    }
    logger.info("通知发送结果: %s", results)
    return results
