"""
conftest.py — 接口自动化测试全局配置
- 统一添加项目根目录到 sys.path
- 提供 pytest_collect_file 钩子确保 YAML 数据文件被正确识别
"""

import sys
from pathlib import Path

# 将项目根目录加入 Python 搜索路径
# 确保 from utils.xxx / from config.xxx / from testdata.xxx 导入在本地和 CI 环境都可用
sys.path.insert(0, str(Path(__file__).resolve().parent))


def pytest_configure(config):
    """pytest 启动时调用，注册自定义 marker"""
    config.addinivalue_line("markers", "smoke: 冒烟测试")
    config.addinivalue_line("markers", "regression: 回归测试")
