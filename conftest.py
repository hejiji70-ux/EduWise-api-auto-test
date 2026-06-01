import os
import pytest


@pytest.fixture(scope="session")
def admin_client(cfg):
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("CI 环境无后端服务，跳过登录")
    # ... 正常登录逻辑
