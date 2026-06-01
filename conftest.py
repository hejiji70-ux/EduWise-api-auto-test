"""
conftest.py - 接口自动化测试全局 Fixture
提供: cfg / base_url / admin_client / app_client / teacher_client
"""

import sys
import os
import pytest
import yaml
from pathlib import Path

# 将项目根目录加入 Python 搜索路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.api_client import ApiClient


@pytest.fixture(scope="session")
def cfg():
    """加载 config/config.yaml"""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def base_url(cfg):
    """返回接口基础 URL"""
    return cfg["base_url"]


@pytest.fixture(scope="session")
def admin_client(cfg):
    """Admin 管理端客户端（自动登录）"""
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("CI 环境无后端服务，跳过登录")
    client = ApiClient(cfg["base_url"])
    login_cfg = cfg["admin"]
    resp = client.post(login_cfg["login_url"], json={
        "username": login_cfg["username"],
        "password": login_cfg["password"],
    })
    data = ApiClient.assert_ok(resp, "Admin 登录")
    token = data.get("token")
    assert token, "Admin 登录未返回 token"
    client.set_token(token)
    return client


@pytest.fixture(scope="session")
def app_client(cfg):
    """App 学员端客户端（自动登录）"""
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("CI 环境无后端服务，跳过登录")
    client = ApiClient(cfg["base_url"])
    login_cfg = cfg["app"]
    resp = client.post(login_cfg["login_url"], json={
        "username": login_cfg["username"],
        "password": login_cfg["password"],
    })
    data = ApiClient.assert_ok(resp, "App 登录")
    token = data.get("token")
    assert token, "App 登录未返回 token"
    client.set_token(token)
    return client


@pytest.fixture(scope="session")
def teacher_client(cfg):
    """Teacher 讲师端客户端（自动登录）"""
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("CI 环境无后端服务，跳过登录")
    client = ApiClient(cfg["base_url"])
    login_cfg = cfg["teacher"]
    resp = client.post(login_cfg["login_url"], json={
        "username": login_cfg["username"],
        "password": login_cfg["password"],
    })
    data = ApiClient.assert_ok(resp, "Teacher 登录")
    token = data.get("token")
    assert token, "Teacher 登录未返回 token"
    client.set_token(token)
    return client


def pytest_configure(config):
    config.addinivalue_line("markers", "smoke: 冒烟测试")
    config.addinivalue_line("markers", "regression: 回归测试")
