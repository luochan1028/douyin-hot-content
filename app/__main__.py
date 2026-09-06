"""命令行入口：python -m app <command>。"""
import argparse
import asyncio
import sys

from app.logger import get_logger

logger = get_logger("cli")


def cmd_init_db(args):
    from app.database import init_db
    init_db()
    logger.info("数据库初始化完成")


def cmd_crawl(args):
    from app.crawler.runner import run_crawl
    asyncio.run(run_crawl())


def cmd_pipeline(args):
    from app.scheduler.orchestrator import run_full_pipeline
    asyncio.run(run_full_pipeline())


def cmd_scheduler(args):
    from app.scheduler.aps import start_scheduler
    import time
    start_scheduler()
    logger.info("定时调度器已启动，按 Ctrl+C 停止")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        from app.scheduler.aps import stop_scheduler
        stop_scheduler()


def cmd_web(args):
    import uvicorn
    from app.config import settings
    uvicorn.run("app.web.app:app", host=settings.WEB_HOST, port=settings.WEB_PORT, reload=False)


def cmd_health(args):
    from app.notify.health import run_health_check
    result = run_health_check()
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_login(args):
    """登录抖音创作者中心，保存 Cookie。"""
    from app.publisher.login import login, has_cookies, clear_cookies, import_cookies
    if args.logout:
        clear_cookies()
        print("已退出登录")
        return
    # 直接导入 Cookie 模式
    if args.cookies:
        result = import_cookies(args.cookies)
        print(result["message"])
        return
    if args.cookies_file:
        from pathlib import Path
        cookie_text = Path(args.cookies_file).read_text(encoding="utf-8")
        result = import_cookies(cookie_text)
        print(result["message"])
        return
    if has_cookies() and not args.force:
        print("已有登录 Cookie，如需重新登录请加 --force")
        return
    headless = None
    if args.headless:
        headless = True
    elif args.no_headless:
        headless = False
    result = asyncio.run(login(headless=headless, timeout=args.timeout))
    print(result["message"])
    if result.get("qr_screenshot"):
        print(f"二维码截图: {result['qr_screenshot']}")


def cmd_login_status(args):
    """检查抖音登录状态。"""
    from app.publisher.login import check_login_status
    result = asyncio.run(check_login_status())
    print(f"登录状态: {'已登录' if result['logged_in'] else '未登录'}")
    print(result["message"])


def main():
    parser = argparse.ArgumentParser(prog="douyin-hot", description="抖音热点内容自动生成与发布系统")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="初始化数据库").set_defaults(func=cmd_init_db)
    sub.add_parser("crawl", help="执行一次热点抓取").set_defaults(func=cmd_crawl)
    sub.add_parser("pipeline", help="执行一次完整生产流水线").set_defaults(func=cmd_pipeline)
    sub.add_parser("scheduler", help="启动定时调度器").set_defaults(func=cmd_scheduler)
    sub.add_parser("web", help="启动 Web 管理后台").set_defaults(func=cmd_web)
    sub.add_parser("health", help="健康检查").set_defaults(func=cmd_health)

    login_p = sub.add_parser("login", help="登录抖音创作者中心")
    login_p.add_argument("--force", action="store_true", help="强制重新登录")
    login_p.add_argument("--logout", action="store_true", help="退出登录（清除 Cookie）")
    login_p.add_argument("--headless", action="store_true", help="无头模式（云服务器用）")
    login_p.add_argument("--no-headless", action="store_true", help="有界面模式（本地用）")
    login_p.add_argument("--timeout", type=int, default=300, help="登录等待超时秒数")
    login_p.add_argument("--cookies", type=str, default=None, help='直接粘贴 Cookie 字符串，如 "sessionid=xxx; ttwid=yyy"')
    login_p.add_argument("--cookies-file", type=str, default=None, help="从文件读取 Cookie（支持 .txt 或 .json）")
    login_p.set_defaults(func=cmd_login)

    sub.add_parser("login-status", help="检查抖音登录状态").set_defaults(func=cmd_login_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
