"""HTTP 客户端工具。"""
import httpx

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


async def async_get(url: str, timeout: float = 15.0, headers: dict = None, **kwargs) -> httpx.Response:
    hdrs = {**DEFAULT_HEADERS, **(headers or {})}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        return await client.get(url, headers=hdrs, **kwargs)


def sync_get(url: str, timeout: float = 15.0, headers: dict = None, **kwargs) -> httpx.Response:
    hdrs = {**DEFAULT_HEADERS, **(headers or {})}
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        return client.get(url, headers=hdrs, **kwargs)


def sync_post(url: str, json: dict = None, timeout: float = 15.0, headers: dict = None, **kwargs) -> httpx.Response:
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        return client.post(url, json=json, headers=hdrs, **kwargs)
