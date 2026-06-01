"""
data_loader.py — YAML 测试数据加载工具
从 YAML 文件加载测试用例数据，供 pytest 参数化使用
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List


TESTDATA_DIR = Path(__file__).parent.parent / "testdata"


def load_yaml(filepath: str) -> Any:
    """加载任意 YAML 文件，返回解析后的 Python 对象"""
    full_path = Path(filepath)
    if not full_path.is_absolute():
        full_path = TESTDATA_DIR / filepath
    with open(full_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_cases(filepath: str) -> List[Dict[str, Any]]:
    """
    加载测试用例列表
    支持两种 YAML 格式：
      - 带 cases 节点：{cases: [{id: "login_001", ...}]}
      - 直接是列表：[{id: "login_001", ...}]
    """
    data = load_yaml(filepath)
    if isinstance(data, dict) and "cases" in data:
        return data["cases"]
    if isinstance(data, list):
        return data
    raise ValueError(
        f"YAML 格式错误: {filepath}，期望包含 'cases' 列表或本身就是列表"
    )


def get_case_ids(cases: List[Dict[str, Any]]) -> List[str]:
    """
    从用例列表中提取 ID 列表
    配合 @pytest.mark.parametrize(ids=...) 使用，
    让报告中显示可读名称而非 case[0]/case[1]
    """
    ids = []
    for i, case in enumerate(cases):
        case_id = case.get("id") or case.get("title") or f"case_{i}"
        ids.append(str(case_id))
    return ids


def load_config() -> Dict[str, Any]:
    """加载全局配置文件 config/config.yaml"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
