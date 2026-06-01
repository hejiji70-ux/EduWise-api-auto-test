"""
api_client.py — HTTP 请求客户端封装
EduWise 三端（Admin / App / Teacher）接口测试的通用请求层
"""

import requests
import yaml
import json as _json
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


def load_config() -> dict:
    """加载 config/config.yaml"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class ApiClient:
    """
    EduWise 接口测试客户端
    封装 requests.Session，统一处理 URL 拼接、Token 管理、请求/响应日志、断言
    支持 Admin / App / Teacher 三端（仅登录账号不同）
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self._token = None
        logger.info(f"ApiClient 初始化: base_url={self.base_url}")

    def set_token(self, token: str):
        """设置认证 Token，之后所有请求自动携带 X-Token header"""
        self._token = token
        self.session.headers.update({"X-Token": token})
        logger.info(f"Token 已设置: {token[:20]}..." if token else "Token 已清除")

    def clear_token(self):
        """清除 Token（用于测试未授权访问场景）"""
        self._token = None
        self.session.headers.pop("X-Token", None)
        logger.info("Token 已清除")

    @property
    def token(self):
        return self._token

    # ── HTTP 方法封装 ────────────────────────────────────────

    def _log_request(self, method: str, url: str, **kwargs):
        logger.debug(f"▶ {method} {url}")
        if "json" in kwargs:
            logger.debug(f"  Body(JSON): {_json.dumps(kwargs['json'], ensure_ascii=False)[:500]}")
        if "data" in kwargs:
            logger.debug(f"  Body(Form): {str(kwargs['data'])[:500]}")
        if "params" in kwargs:
            logger.debug(f"  Query: {kwargs['params']}")

    def _log_response(self, resp: requests.Response):
        logger.debug(f"◀ HTTP {resp.status_code} ({resp.elapsed.total_seconds()*1000:.0f}ms)")
        try:
            body = resp.json()
            status = body.get("status")
            msg = body.get("message", "")
            logger.debug(f"  status={status}, message={msg}")
            if status != 200:
                logger.warning(f"  业务异常: status={status}, msg={msg}")
        except Exception:
            logger.debug(f"  响应文本: {resp.text[:300]}")

    def get(self, path: str, **kwargs) -> requests.Response:
        url = self.base_url + path
        self._log_request("GET", url, **kwargs)
        resp = self.session.get(url, **kwargs)
        self._log_response(resp)
        return resp

    def post(self, path: str, **kwargs) -> requests.Response:
        """
        POST 请求
        特殊处理：当传了 files 参数（multipart/form-data 上传）时，
        必须临时移除 Content-Type: application/json，让 requests 自动设置 boundary
        """
        url = self.base_url + path
        self._log_request("POST", url, **kwargs)

        if "files" in kwargs:
            orig_ct = self.session.headers.pop("Content-Type", None)
            try:
                resp = self.session.post(url, **kwargs)
            finally:
                if orig_ct:
                    self.session.headers["Content-Type"] = orig_ct
            self._log_response(resp)
            return resp

        resp = self.session.post(url, **kwargs)
        self._log_response(resp)
        return resp

    def put(self, path: str, **kwargs) -> requests.Response:
        url = self.base_url + path
        self._log_request("PUT", url, **kwargs)
        resp = self.session.put(url, **kwargs)
        self._log_response(resp)
        return resp

    def delete(self, path: str, **kwargs) -> requests.Response:
        url = self.base_url + path
        self._log_request("DELETE", url, **kwargs)
        resp = self.session.delete(url, **kwargs)
        self._log_response(resp)
        return resp

    # ── 断言方法 ──────────────────────────────────────────────

    @staticmethod
    def assert_ok(resp: requests.Response, msg: str = "") -> object:
        """
        断言接口返回成功（HTTP 200 + 业务 status=200）
        返回 data 字段内容供后续断言使用
        """
        assert resp.status_code == 200, (
            f"{msg} | HTTP {resp.status_code}: {resp.text[:300]}"
        )
        body = resp.json()
        assert body.get("status") == 200, (
            f"{msg} | business status={body.get('status')}, "
            f"message={body.get('message')}, body={resp.text[:300]}"
        )
        logger.info(f"✓ {msg} | 断言通过")
        return body.get("data")

    @staticmethod
    def assert_fail(resp: requests.Response, expected_status: int = None, msg: str = "") -> dict:
        """
        断言接口返回预期的业务错误
        expected_status 非空时精确匹配错误码；否则只要 status != 200 即通过
        返回完整响应 body
        """
        assert resp.status_code == 200, (
            f"{msg} | HTTP {resp.status_code}: {resp.text[:300]}"
        )
        body = resp.json()
        if expected_status:
            assert body.get("status") == expected_status, (
                f"{msg} | expected status={expected_status}, "
                f"got status={body.get('status')}, message={body.get('message')}"
            )
        else:
            assert body.get("status") != 200, (
                f"{msg} | 期望接口返回错误，但实际返回了 status=200"
            )
        logger.info(f"✓ {msg} | 预期失败断言通过: status={body.get('status')}")
        return body
