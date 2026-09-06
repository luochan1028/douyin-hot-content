"""FastAPI Web 管理后台。"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from sqlalchemy import desc

from app.database import SessionLocal
from app.models import Hotspot, MediaAsset, PublishRecord, ReviewTicket
from app.notify.health import run_health_check
from app.config import settings, account_tags, STORAGE_DIR
from app.logger import get_logger

logger = get_logger("web.app")

app = FastAPI(title="抖音热点内容自动生成与发布系统")


@app.get("/health")
def health():
    return run_health_check()


@app.get("/api/hotspots")
def list_hotspots(limit: int = Query(50, ge=1, le=500),
                  lifecycle: Optional[str] = None,
                  review_status: Optional[str] = None):
    db = SessionLocal()
    try:
        q = db.query(Hotspot)
        if lifecycle:
            q = q.filter(Hotspot.lifecycle == lifecycle)
        if review_status:
            q = q.filter(Hotspot.review_status == review_status)
        items = q.order_by(desc(Hotspot.heat_score)).limit(limit).all()
        return [
            {
                "id": h.id, "word": h.word, "heat_score": h.heat_score,
                "lifecycle": h.lifecycle, "credibility_score": h.credibility_score,
                "review_status": h.review_status, "category": h.category,
                "source": h.source, "tags": h.tags, "crawl_time": h.crawl_time.isoformat() if h.crawl_time else None,
            }
            for h in items
        ]
    finally:
        db.close()


@app.get("/api/publish-records")
def list_publish_records(limit: int = Query(50, ge=1, le=200)):
    db = SessionLocal()
    try:
        items = db.query(PublishRecord).order_by(desc(PublishRecord.created_at)).limit(limit).all()
        return [
            {
                "id": r.id, "hotspot_word": r.hotspot_word, "status": r.status,
                "copy_content": r.copy_content[:100], "tags": r.tags,
                "error_msg": r.error_msg, "publish_time": r.publish_time.isoformat() if r.publish_time else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in items
        ]
    finally:
        db.close()


@app.get("/api/tickets")
def list_tickets(status: Optional[str] = None):
    db = SessionLocal()
    try:
        q = db.query(ReviewTicket)
        if status:
            q = q.filter(ReviewTicket.status == status)
        items = q.order_by(desc(ReviewTicket.created_at)).all()
        return [
            {
                "id": t.id, "hotspot_word": t.hotspot_word,
                "credibility_score": t.credibility_score, "risk_hint": t.risk_hint,
                "category_result": t.category_result, "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in items
        ]
    finally:
        db.close()


@app.post("/api/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: int, status: str = Query(..., regex="^(approved|rejected)$")):
    from app.accuracy.review import resolve_ticket as do_resolve
    ok = do_resolve(ticket_id, status)
    return {"success": ok}


@app.get("/api/config")
def get_config():
    return {
        "account_category": settings.ACCOUNT_CATEGORY,
        "account_tags": account_tags(),
        "copywriting_style": settings.COPYWRITING_STYLE,
        "daily_publish_limit": settings.DAILY_PUBLISH_LIMIT,
        "crawl_peak_interval": settings.CRAWL_PEAK_INTERVAL,
        "crawl_offpeak_interval": settings.CRAWL_OFFPEAK_INTERVAL,
    }


@app.post("/api/login")
def api_login(force: bool = False):
    """启动抖音登录（headless 模式，生成二维码截图）。"""
    from app.publisher.login import login, has_cookies
    if has_cookies() and not force:
        return {"success": True, "message": "已有登录 Cookie", "need_scan": False}
    result = asyncio.run(login(headless=True, timeout=300))
    return {
        "success": result["success"],
        "message": result["message"],
        "qr_url": "/api/login/qr" if result.get("qr_screenshot") else "",
    }


@app.get("/api/login/qr")
def api_login_qr():
    """返回登录二维码截图。"""
    qr = STORAGE_DIR / "douyin_qr.png"
    if qr.exists():
        return FileResponse(str(qr), media_type="image/png")
    return JSONResponse({"error": "二维码不存在，请先调用 /api/login"}, status_code=404)


@app.get("/api/login/status")
def api_login_status():
    """检查抖音登录状态。"""
    from app.publisher.login import check_login_status
    result = asyncio.run(check_login_status())
    return result


@app.post("/api/login/logout")
def api_logout():
    """清除登录 Cookie。"""
    from app.publisher.login import clear_cookies
    clear_cookies()
    return {"success": True, "message": "已退出登录"}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>抖音热点内容自动生成与发布系统</title>
<style>
body{font-family:-apple-system,"Microsoft YaHei",sans-serif;margin:0;background:#f5f7fa;color:#333}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:20px 40px}
.header h1{margin:0;font-size:22px}
.header .sub{font-size:13px;opacity:.8;margin-top:6px}
.container{padding:20px 40px}
.card{background:#fff;border-radius:10px;padding:20px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.card h2{margin:0 0 15px;font-size:16px;border-left:4px solid #4361ee;padding-left:10px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:10px;text-align:left;border-bottom:1px solid #eee}
th{background:#f8f9fa;font-weight:600}
.tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;margin-right:4px}
.burst{background:#fee2e2;color:#dc2626}
.sprout{background:#fef3c7;color:#d97706}
.approved{background:#dcfce7;color:#16a34a}
.rejected{background:#f3f4f6;color:#6b7280}
.review{background:#dbeafe;color:#2563eb}
.stats{display:flex;gap:16px;margin-bottom:20px}
.stat{flex:1;background:#fff;border-radius:10px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.stat .num{font-size:28px;font-weight:bold;color:#4361ee}
.stat .label{font-size:13px;color:#6b7280;margin-top:4px}
</style>
</head>
<body>
<div class="header">
  <h1>抖音热点内容自动生成与发布系统</h1>
  <div class="sub">零成本 · 全自动 · 热点抓取 → 内容生成 → 定时发布</div>
</div>
<div class="container">
  <div class="stats" id="stats"></div>
  <div class="card">
    <h2>抖音账号登录</h2>
    <div id="login-box">
      <p>登录状态: 检测中...</p>
    </div>
  </div>
  <div class="card">
    <h2>热点列表（爆发期优先）</h2>
    <table>
      <thead><tr><th>ID</th><th>热点词</th><th>分类</th><th>热度分</th><th>可信度</th><th>生命周期</th><th>审核</th><th>标签</th></tr></thead>
      <tbody id="hotspots"></tbody>
    </table>
  </div>
  <div class="card">
    <h2>发布记录</h2>
    <table>
      <thead><tr><th>ID</th><th>热点</th><th>状态</th><th>文案预览</th><th>错误</th><th>时间</th></tr></thead>
      <tbody id="records"></tbody>
    </table>
  </div>
</div>
<script>
async function load(){
  const hs = await fetch('/api/hotspots?limit=20').then(r=>r.json());
  const burst = hs.filter(h=>h.lifecycle==='爆发期').length;
  const approved = hs.filter(h=>h.review_status==='approved').length;
  const recs = await fetch('/api/publish-records?limit=10').then(r=>r.json());
  const pub = recs.filter(r=>r.status==='success').length;
  document.getElementById('stats').innerHTML = `
    <div class="stat"><div class="num">${hs.length}</div><div class="label">热点总数</div></div>
    <div class="stat"><div class="num">${burst}</div><div class="label">爆发期</div></div>
    <div class="stat"><div class="num">${approved}</div><div class="label">已通过</div></div>
    <div class="stat"><div class="num">${pub}</div><div class="label">发布成功</div></div>`;
  document.getElementById('hotspots').innerHTML = hs.map(h=>`<tr>
    <td>${h.id}</td><td>${h.word}</td><td>${h.category||'-'}</td>
    <td>${h.heat_score?.toFixed(1)||0}</td><td>${h.credibility_score?.toFixed(1)||0}</td>
    <td><span class="tag ${h.lifecycle==='爆发期'?'burst':h.lifecycle==='萌芽期'?'sprout':''}">${h.lifecycle}</span></td>
    <td><span class="tag ${h.review_status}">${h.review_status}</span></td>
    <td>${(h.tags||'').slice(0,40)}</td></tr>`).join('');
  document.getElementById('records').innerHTML = recs.map(r=>`<tr>
    <td>${r.id}</td><td>${r.hotspot_word}</td>
    <td><span class="tag ${r.status==='success'?'approved':'rejected'}">${r.status}</span></td>
    <td>${r.copy_content||''}</td><td>${r.error_msg||''}</td>
    <td>${r.publish_time||r.created_at||''}</td></tr>`).join('');
}
load();
loadLogin();

async function loadLogin(){
  try {
    const s = await fetch('/api/login/status').then(r=>r.json());
    const box = document.getElementById('login-box');
    if (s.logged_in) {
      box.innerHTML = `<p><span class="tag approved">已登录</span> ${s.message}</p>
        <button onclick="logout()" style="margin-top:8px;padding:6px 16px;background:#ef4444;color:#fff;border:none;border-radius:4px;cursor:pointer">退出登录</button>`;
    } else {
      box.innerHTML = `<p><span class="tag rejected">未登录</span> ${s.message}</p>
        <button onclick="doLogin()" style="margin-top:8px;padding:6px 16px;background:#4361ee;color:#fff;border:none;border-radius:4px;cursor:pointer">扫码登录</button>
        <div id="qr-box" style="margin-top:12px"></div>`;
    }
  } catch(e) { document.getElementById('login-box').innerHTML = '<p>登录状态检测失败</p>'; }
}

async function doLogin(){
  const box = document.getElementById('qr-box');
  box.innerHTML = '<p>正在生成二维码，请稍候...</p>';
  const r = await fetch('/api/login', {method:'POST'}).then(r=>r.json());
  if (r.qr_url) {
    box.innerHTML = `<p>请用抖音 App 扫描下方二维码：</p><img src="${r.qr_url}" style="max-width:280px;border:1px solid #ddd"><p style="margin-top:8px;color:#666">扫码后请稍候，系统会自动检测登录状态...</p>
      <button onclick="loadLogin()" style="margin-top:8px;padding:6px 16px;background:#16a34a;color:#fff;border:none;border-radius:4px;cursor:pointer">我已扫码，刷新状态</button>`;
  } else {
    box.innerHTML = `<p style="color:#ef4444">${r.message}</p>`;
  }
}

async function logout(){
  await fetch('/api/login/logout', {method:'POST'});
  loadLogin();
}
</script>
</body>
</html>
"""
